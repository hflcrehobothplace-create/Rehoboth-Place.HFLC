# ==============================================
# app.py - UPDATED FOR PRODUCTION
# Holyghost Family Life Centre Inc.
# ==============================================

import requests
import psycopg2  # OLD: import sqlite3
from psycopg2.extras import RealDictCursor
import os
from flask import Flask, render_template, request, redirect, flash, session, url_for
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ------------------------------------------
# INITIALIZE APP
# ------------------------------------------

app = Flask(__name__)

# OLD: app.secret_key = "supersecretchurchkey"
# NEW: Secret key is now pulled from Render settings for security
app.secret_key = os.environ.get("FLASK_KEY", "fallback-key-for-local-testing")


# ------------------------------------------
# DATABASE CONNECTION HELPER
# ------------------------------------------
def get_db_connection():
    """Connects to the external PostgreSQL database."""
    # This URL will come from Neon.tech or Supabase
    db_url = os.environ.get("DATABASE_URL")
    return psycopg2.connect(db_url)

def init_db():
    """Creates the table if it doesn't exist (Postgres syntax)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # OLD: id INTEGER PRIMARY KEY AUTOINCREMENT
    # NEW: id SERIAL PRIMARY KEY (Postgres way)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signups (
            id SERIAL PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

with app.app_context():
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

    conn = get_db_connection()
    cursor = conn.cursor()
    # OLD: VALUES (?, ?, ?)
    # NEW: VALUES (%s, %s, %s) (Postgres uses %s)
    cursor.execute('''
        INSERT INTO signups (full_name, email, phone)
        VALUES (%s, %s, %s)
    ''', (full_name, email, phone))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Thank you! You are now connected with our church.")
    return redirect('/')

# ------------------------------------------
# ROUTE 3: Bible Verse Search (No changes needed, logic was perfect)
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
# OLD: Hardcoded username/password
# NEW: Pulled from Render Environment Variables
ADMIN_USERNAME = os.environ.get("ADMIN_USER")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS")

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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signups")
    signups = cursor.fetchall()
    cursor.close()
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
# ROUTE 7: Send Announcements
# ------------------------------------------
@app.route('/send-message', methods=['POST'])
def send_message():
    if not session.get('admin_logged_in'):
        flash("Unauthorized. Please log in as admin.")
        return redirect(url_for('admin_login'))

    TWILIO_SID = os.environ.get("TWILIO_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE = os.environ.get("TWILIO_PHONE", "")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
    FROM_EMAIL = os.environ.get("FROM_EMAIL", "")

    announcement = request.form.get('announcement', 'Greetings from HFLC!')

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT email, phone FROM signups")
    contacts = c.fetchall()
    c.close()
    conn.close()

    sms_sent = 0
    email_sent = 0

    for email, phone in contacts:
        if phone and TWILIO_SID:
            try:
                client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
                client.messages.create(body=announcement, from_=TWILIO_PHONE, to=phone)
                sms_sent += 1
            except Exception as e:
                print(f"SMS failed: {e}")

        if email and SENDGRID_API_KEY:
            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                msg = Mail(from_email=FROM_EMAIL, to_emails=email, subject="Church Update", plain_text_content=announcement)
                sg.send(msg)
                email_sent += 1
            except Exception as e:
                print(f"Email failed: {e}")

    flash(f"Sent! SMS: {sms_sent}, Emails: {email_sent}")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

