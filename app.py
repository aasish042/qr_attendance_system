from flask import Flask, render_template, request, redirect, url_for, session, send_file
import qrcode
import csv
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'  # Session secure rakhne ke liye

CSV_FILE = 'attendance.csv'

# Ensure static folder exists on startup
if not os.path.exists('static'):
    os.makedirs('static')

# Agar CSV file nahi hai toh header ke sath bana lein
def init_csv():
    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Name', 'Roll Number', 'Branch', 'Subject'])

init_csv()

# Root URL ko direct Admin Login par redirect karne ke liye
@app.route('/')
def home():
    return redirect(url_for('admin_login'))

# 1. Admin Login Route
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Galat Username ya Password hai!'
    return render_template('login.html', error=error)

# 2. Admin Dashboard & QR Generator
@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Render ya local host ke hisab se automatic URL detect karna
        host_url = request.host_url.rstrip('/')
        target_url = f"{host_url}/mark"
        
        # QR Code Generate karke save karna
        img = qrcode.make(target_url)
        qr_path = os.path.join('static', 'qr_code.png')
        img.save(qr_path)
    except Exception as e:
        print(f"QR Generation Error: {e}")

    # Saari attendance records read karna table ke liye
    records = []
    if os.path.isfile(CSV_FILE):
        try:
            with open(CSV_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                records = list(reader)
        except Exception as e:
            print(f"CSV Read Error: {e}")
            
    return render_template('dashboard.html', records=records)

# 3. Download CSV Report Route
@app.route('/download-report')
def download_report():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    if os.path.isfile(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "No records found!", 404

# 4. Admin Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

# 5. Student Attendance Form Route
@app.route('/mark', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        name = request.form.get('name')
        roll = request.form.get('roll')
        branch = request.form.get('branch')
        subject = request.form.get('subject')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, name, roll, branch, subject])
        except Exception as e:
            return f"Error saving attendance: {e}", 500
            
        return "<h2 style='text-align:center; color:green; margin-top:20vh;'>Attendance Successfully Recorded! Thank you.</h2>"
    
    return render_template('attendance.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
