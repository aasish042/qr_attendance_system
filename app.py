from flask import Flask, render_template, request, redirect, url_for, session, send_file
import qrcode
import csv
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_professional_key'

CSV_FILE = 'attendance.csv'

if not os.path.exists('static'):
    os.makedirs('static')

def init_csv():
    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Name', 'Roll Number', 'Branch', 'Subject'])

init_csv()

@app.route('/')
def home():
    return redirect(url_for('admin_login'))

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
            error = 'Invalid Username or Password!'
    return render_template('login.html', error=error)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        host_url = request.host_url.rstrip('/')
        target_url = f"{host_url}/mark"
        img = qrcode.make(target_url)
        qr_path = os.path.join('static', 'qr_code.png')
        img.save(qr_path)
    except Exception as e:
        print(f"QR Error: {e}")

    records = []
    if os.path.isfile(CSV_FILE):
        try:
            with open(CSV_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                records = list(reader)
        except Exception as e:
            print(f"CSV Error: {e}")
            
    return render_template('dashboard.html', records=records)

@app.route('/download-report')
def download_report():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    if os.path.isfile(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "No records found!", 404

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

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
            return f"Error: {e}", 500
            
        return render_template('success.html')
    
    return render_template('attendance.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
