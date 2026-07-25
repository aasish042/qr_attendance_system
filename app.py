from flask import Flask, render_template, request, redirect, url_for, session, send_file
import qrcode
import io
import base64
import csv
import os
import time
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = 'super_secret_professional_key'

CSV_FILE = 'attendance.csv'
PDF_FILE = 'attendance_report.pdf'

# Session / Token storage for QR Expiry (2 Minutes = 120 seconds) - UPDATED
active_session = {
    "token": None,
    "expires_at": 0
}

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
    
    qr_b64 = ""
    target_url = ""
    try:
        host_url = request.host_url.rstrip('/')
        
        # Unique token aur 2 minute (120 seconds) ki expiry set karna - UPDATED
        token = str(int(time.time()))
        active_session["token"] = token
        active_session["expires_at"] = time.time() + 120  # 2 minutes valid
        
        # Link mein token pass hoga
        target_url = f"{host_url}/mark?token={token}"
        
        # QR code ko memory mein generate karke Base64 string banana
        img = qrcode.make(target_url)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
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
            
    return render_template('dashboard.html', records=records, qr_b64=qr_b64, target_url=target_url)

@app.route('/download-report')
def download_report():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    if os.path.isfile(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "No records found!", 404

@app.route('/download-pdf')
def download_pdf():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    if not os.path.isfile(CSV_FILE):
        return "No records found!", 404
        
    try:
        data = []
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)
            
        if not data:
            return "No records found!", 404

        # Generate PDF using ReportLab
        doc = SimpleDocTemplate(PDF_FILE, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#0f172a'),
            alignment=1,
            spaceAfter=20
        )
        
        elements.append(Paragraph("Smart QR Attendance Report", title_style))
        elements.append(Spacer(1, 10))
        
        # Format table data for ReportLab
        table_data = []
        for row in data:
            table_data.append([Paragraph(cell, styles['Normal']) for cell in row])
            
        t = Table(table_data, colWidths=[110, 110, 95, 90, 135])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
        ]))
        
        elements.append(t)
        doc.build(elements)
        
        return send_file(PDF_FILE, as_attachment=True)
    except Exception as e:
        return f"PDF Generation Error: {e}", 500

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/mark', methods=['GET', 'POST'])
def mark_attendance():
    # Token check for expiry validation - UPDATED
    token = request.args.get('token') or request.form.get('token')
    current_time = time.time()
    if not token or token != active_session["token"] or current_time > active_session["expires_at"]:
        return """
        <div style='text-align:center; margin-top:20vh; font-family:sans-serif;'>
            <h2 style='color:red;'>❌ Attendance Link Expired!</h2>
            <p>Yeh QR code ya link expire ho chuka hai (2 minutes limit exceeded). Kripya naya QR scan karein.</p>
        </div>
        """, 403

    if request.method == 'POST':
        name = request.form.get('name')
        roll = request.form.get('roll')
        branch = request.form.get('branch')
        subject = request.form.get('subject')
        
        # UPDATED: Live exact precise real-time timestamp generation on form submit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, name, roll, branch, subject])
        except Exception as e:
            return f"Error: {e}", 500
            
        return render_template('success.html')
    
    return render_template('attendance.html', token=token)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
