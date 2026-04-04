# ==============================================
# app.py - Flask Backend for Church Website
# Holyghost Family Life Centre Inc.
# ==============================================

import requests
import sqlite3
import os
from flask import Flask, render_template, request, redirect, flash, session, url_for
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ------------------------------------------
# INITIALIZE APP
# ------------------------------------------
app = Flask(__name__)
app.secret_key = "supersecretchurchkey"

# ------------------------------------------
# DATABASE SETUP
# ------------------------------------------
def init_db():
    """Creates the database and signups table if it doesn't exist."""
    conn = sqlite3.connect('church_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ------------------------------------------
# ROUTE 1: Homepage
# ------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

# ------------------------------------------
# ROUTE 2: Signup Form Submission
# ------------------------------------------
@app.route('/submit-signup', methods=['POST'])
def submit_signup():
    full_name = request.form.get('fullname')
    email = request.form.get('email')
    phone = request.form.get('phone')

    if not full_name or not email or not phone:
        flash("Please fill in all fields.")
        return redirect('/')

    conn = sqlite3.connect('church_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO signups (full_name, email, phone)
        VALUES (?, ?, ?)
    ''', (full_name, email, phone))
    conn.commit()
    conn.close()

    flash("Thank you! You are now connected with our church.")
    return redirect('/')

# ------------------------------------------
# ROUTE 3: Bible Verse Search
# ------------------------------------------
@app.route('/bible-search', methods=['GET', 'POST'])
def bible_search():
    verse_text = None
    verse_ref = None
    error = None

    if request.method == 'POST':
        verse_query = request.form.get('verse', '').strip()

        if not verse_query:
            error = "Please enter a verse (e.g., John 3:16)."
        else:
            try:
                response = requests.get(
                    f"https://bible-api.com/{verse_query}?translation=kjv",
                    timeout=10
                )
                data = response.json()

                if 'error' in data:
                    error = "Verse not found. Try a valid reference like John 3:16 or Psalm 23."
                else:
                    verse_text = data.get('text', '').strip()
                    verse_ref = data.get('reference', verse_query)

            except Exception as e:
                error = "Could not connect to Bible API. Please try again."

    return render_template('bible.html', verse_text=verse_text, verse_ref=verse_ref, error=error)

# ------------------------------------------
# ROUTE 4: Admin Login
# ------------------------------------------
ADMIN_USERNAME = "jeffery"
ADMIN_PASSWORD = "2025rehoboth"

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash("Welcome, Admin!")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password.")

    return render_template('adminlogins.html')

# ------------------------------------------
# ROUTE 5: Admin Dashboard
# ------------------------------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash("Please log in first.")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('church_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signups")
    signups = cursor.fetchall()
    conn.close()

    return render_template('admin.html', signups=signups)

# ------------------------------------------
# ROUTE 6: Logout
# ------------------------------------------
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("You have been logged out.")
    return redirect('/')

# ------------------------------------------
# ROUTE 7: Send Announcements (SMS + Email)
# ------------------------------------------
@app.route('/send-message', methods=['POST'])
def send_message():
    if not session.get('admin_logged_in'):
        flash("Unauthorized. Please log in as admin.")
        return redirect(url_for('admin_login'))

    # Read keys from environment variables
    TWILIO_SID = os.environ.get("TWILIO_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE = os.environ.get("TWILIO_PHONE", "")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
    FROM_EMAIL = os.environ.get("FROM_EMAIL", "")

    announcement = request.form.get('announcement', 'Greetings from Holyghost Family Life Centre!')

    conn = sqlite3.connect('church_data.db')
    c = conn.cursor()
    c.execute("SELECT email, phone FROM signups")
    contacts = c.fetchall()
    conn.close()

    sms_sent = 0
    email_sent = 0

    for email, phone in contacts:
        # Send SMS via Twilio
        if phone and TWILIO_SID:
            try:
                client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
                client.messages.create(
                    body=announcement,
                    from_=TWILIO_PHONE,
                    to=phone
                )
                sms_sent += 1
            except Exception as e:
                print(f"SMS failed to {phone}: {e}")

        # Send Email via SendGrid
        if email and SENDGRID_API_KEY:
            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                msg = Mail(
                    from_email=FROM_EMAIL,
                    to_emails=email,
                    subject="Church Announcement - HFLC",
                    plain_text_content=announcement
                )
                sg.send(msg)
                email_sent += 1
            except Exception as e:
                print(f"Email failed to {email}: {e}")

    flash(f"Announcement sent! SMS: {sms_sent}, Emails: {email_sent}")
    return redirect(url_for('admin_dashboard'))

# ------------------------------------------
# RUN APP
# ------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

