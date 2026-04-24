# ==============================================
# app.py - UPDATED FOR PRODUCTION
# Holyghost Family Life Centre Inc.
# ==============================================

import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, flash, session, url_for

# ------------------------------------------
# INITIALIZE APP
# ------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_KEY", "fallback-key-for-local-testing")


# ------------------------------------------
# DATABASE CONNECTION HELPER
# ------------------------------------------
def get_db_connection():
    """Connects to the external PostgreSQL database."""
    db_url = os.environ.get("DATABASE_URL")
    return psycopg2.connect(db_url)

def init_db():
    """Creates the table if it doesn't exist (Postgres syntax)."""
    conn = get_db_connection()
    cursor = conn.cursor()
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
# ROUTE 7: Send Announcements via Gmail
# ------------------------------------------
@app.route('/send-message', methods=['POST'])
def send_message():
    if not session.get('admin_logged_in'):
        flash("Unauthorized. Please log in as admin.")
        return redirect(url_for('admin_login'))

    # Gmail credentials from Render environment variables
    GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

    announcement = request.form.get('announcement', 'Greetings from Holyghost Family Life Centre!')

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        flash("Email not configured. Please set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in Render environment variables.")
        return redirect(url_for('admin_dashboard'))

    # Get all signups from database
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT full_name, email FROM signups")
    contacts = c.fetchall()
    c.close()
    conn.close()

    if not contacts:
        flash("No contacts found in the database yet.")
        return redirect(url_for('admin_dashboard'))

    email_sent = 0
    email_failed = 0

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)

        for full_name, recipient_email in contacts:
            try:
                # Build the email
                msg = MIMEMultipart()
                msg['From'] = f"Holyghost Family Life Centre <{GMAIL_ADDRESS}>"
                msg['To'] = recipient_email
                msg['Subject'] = "Church Announcement - Holyghost Family Life Centre"

                # Email body
                body = f"""Dear {full_name},

{announcement}

God bless you,
Holyghost Family Life Centre Inc.
(Rehoboth Place)
Owerri, Imo State, Nigeria.

---
To unsubscribe, reply to this email.
"""
                msg.attach(MIMEText(body, 'plain'))
                server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_string())
                email_sent += 1

            except Exception as e:
                print(f"Failed to send to {recipient_email}: {e}")
                email_failed += 1

        server.quit()

    except Exception as e:
        flash(f"Could not connect to Gmail: {str(e)}")
        return redirect(url_for('admin_dashboard'))

    flash(f"Announcement sent! Emails delivered: {email_sent}, Failed: {email_failed}")
    return redirect(url_for('admin_dashboard'))


# ------------------------------------------
# RUN APP
# ------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

