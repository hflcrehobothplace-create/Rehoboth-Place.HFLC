# ==============================================
# app.py — Flask Backend for Church Website + Admin Panel
# ==============================================
# pip install twilio sendgrid
# Twilio for SMS
from twilio.rest import Client



# for bible search Import requests at the top of app.py if not already imported
import requests
from flask import render_template, request, flash, redirect





# SendGrid for Email
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import Flask, render_template, request, redirect, flash, session, url_for
import sqlite3
import os


# Initialize the Flask app
app = Flask(__name__)
app.secret_key = "supersecretchurchkey"


# ------------------------------------------
# DATABASE SETUP
# ------------------------------------------
def init_db():

    """Creates the database and signups table if not exists."""
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

# Run DB setup
init_db()

# ------------------------------------------
# ROUTE 1: Homepage
# ------------------------------------------
@app.route('/')
def home():
    """Render homepage (2chweb.html)."""
    return render_template('2chweb.html')

# ------------------------------------------
# ROUTE 2: Handle Form Submission
# ------------------------------------------
@app.route('/submit-signup', methods=['POST'])
def submit_signup():
    """Handles user signup form submission."""
    full_name = request.form.get('fullname')
    email = request.form.get('email')
    phone = request.form.get('phone')

    # Validate fields
    if not full_name or not email or not phone:
        flash("⚠️ Please fill in all fields.")
        return redirect('/')

    # Insert into database safely
    conn = sqlite3.connect('church_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO signups (full_name, email, phone)
        VALUES (?, ?, ?)
    ''', (full_name, email, phone))
    conn.commit()
    conn.close()

    flash("✅ Thank you! You are now connected with our church.")
    return redirect('/')

# ------------------------------------------
# ADMIN SYSTEM
# ------------------------------------------

# Temporary admin credentials (you can change them)
ADMIN_USERNAME = "jeffery"
ADMIN_PASSWORD = "2025rehoboth"

@app.route('/adminlogins', methods=['GET', 'POST'])
def admin_login():
    """Handles admin login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash("✅ Welcome Admin!")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("❌ Invalid credentials.")
            return redirect(url_for('admin_login'))
    
    return render_template('adminlogins.html')

@app.route('/admin')
def admin_dashboard():
    """Displays all signups to admin."""
    if not session.get('admin_logged_in'):
        flash("⚠️ Please log in first.")
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect('church_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signups")
    signups = cursor.fetchall()
    conn.close()

    return render_template('admin.html', signups=signups)

@app.route('/logout')
def logout():
    """Logs the admin out."""
    session.pop('admin_logged_in', None)
    flash("👋 You have been logged out.")
    return redirect('/')









@app.route('/send-message', methods=['POST'])
def send_message():
    # --- Security Check ---
    # Only allow admin to send announcements
    if not session.get('admin_logged_in'):
        flash("Unauthorized access! Please log in as admin.", "danger")
        return redirect('/admin_login')

    # --- Connect to Database ---
    conn = sqlite3.connect('church_data.db')
    c = conn.cursor()
    
    # Fetch all emails and phone numbers
    c.execute("SELECT email, phone FROM signups")
    contacts = c.fetchall()  # List of tuples: [(email1, phone1), (email2, phone2), ...]

    conn.close()

    # --- Announcement Message ---
    message_text = "This is a test announcement from our church."
    # Replace the above string with your real announcement



    # --- Send SMS via Twilio ---
    TWILIO_SID = "YOUR_TWILIO_SID"
    TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
    TWILIO_PHONE_NUMBER = "+1234567890"  # Replace with your Twilio phone number
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

    for email, phone in contacts:
        if phone:  # Make sure phone is not empty
            try:
                twilio_client.messages.create(
                    body=message_text,
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone  # Make sure phone numbers include country code e.g., +2348012345678
                )
            except Exception as e:
                print(f"Failed to send SMS to {phone}: {e}")

    # --- Send Email via SendGrid ---
    SENDGRID_API_KEY = "YOUR_SENDGRID_API_KEY"
    sg_client = SendGridAPIClient(SENDGRID_API_KEY)

    for email, phone in contacts:
        if email:  # Make sure email is not empty
            try:
                mail = Mail(
                    from_email="church@example.com",  # Replace with your verified sender email
                    to_emails=email,
                    subject="Church Announcement",
                    plain_text_content=message_text
                )
                sg_client.send(mail)
            except Exception as e:
                print(f"Failed to send Email to {email}: {e}")

    flash("Announcement sent successfully to all contacts!", "success")
    return redirect('/')
    
    
    
    
    
    
    
    
    
    
    
    
# Import requests at the top of app.py if not already imported
import requests
from flask import render_template, request, flash, redirect

# ===============================================
# Bible Search Route
# ===============================================
@app.route('/bible-search', methods=['GET', 'POST'])
def bible_search():
    verse_text = None  # Will store the result
    error = None       # Will store error messages

    if request.method == 'POST':
        # Get the verse input from the form
        verse_query = request.form.get('verse')
        
        if not verse_query:
            error = "Please enter a verse (e.g., John 3:16)."
        else:
            try:
                # Call Bible API
                response = requests.get(f"https://bible-api.com/{verse_query}?translation=kjv")
                data = response.json()
                
                if 'error' in data:
                    error = "Verse not found. Try a valid reference (e.g., John 3:16)."
                else:
                    verse_text = data['text']  # Extract verse text

            except Exception as e:
                error = "Something went wrong. Please try again."

    # Render bible.html with result or error
    return render_template('bible.html', verse_text=verse_text, error=error)   
    
    
    
    
    
    
    
    
    
    
    
    
    
    


# ------------------------------------------
# RUN APP
# ------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
    
   
 
 
 
 
 
 
