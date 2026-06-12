#!/usr/bin/env python3
"""
Church Formation Guidance - Flask Web Application
100% AI-Automated Church Document Generation Service
"""

from flask import Flask, request, render_template_string, jsonify, send_file
import os
import zipfile
from datetime import datetime
from document_generator import ChurchDocumentGenerator
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = './generated_docs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    """Landing page"""
    with open('index.html', 'r') as f:
        return f.read()

@app.route('/get-started')
def questionnaire():
    """Questionnaire page"""
    with open('questionnaire.html', 'r') as f:
        return f.read()

@app.route('/generate-documents', methods=['POST'])
def generate_documents():
    """Handle document generation request"""

    try:
        # Extract form data
        user_data = {
            'church_name': request.form.get('church_name'),
            'state': request.form.get('state'),
            'email': request.form.get('email'),
            'core_beliefs': request.form.get('core_beliefs'),
            'mission_statement': request.form.get('mission_statement'),
            'tradition': request.form.get('tradition'),
            'governance_model': request.form.get('governance_model'),
            'leadership_structure': request.form.get('leadership_structure'),
            'membership_requirements': request.form.get('membership_requirements'),
            'activities': request.form.getlist('activities'),
            'meeting_frequency': request.form.get('meeting_frequency'),
            'financial_model': request.form.get('financial_model'),
            'special_circumstances': request.form.get('special_circumstances')
        }

        # Get requested documents
        requested_docs = request.form.getlist('documents')
        if not requested_docs:
            # Default to all documents
            requested_docs = [
                'articles_of_faith',
                'bylaws',
                'irs_letter',
                'operating_procedures',
                'meeting_minutes',
                'recordkeeping'
            ]

        # Generate documents
        generator = ChurchDocumentGenerator()
        documents = generator.generate_all_documents(user_data, requested_docs)

        # Save documents
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        church_folder = os.path.join(UPLOAD_FOLDER, f"{user_data['church_name']}_{timestamp}".replace(' ', '_'))
        os.makedirs(church_folder, exist_ok=True)

        # Save individual files
        for filename, content in documents.items():
            filepath = os.path.join(church_folder, filename)
            with open(filepath, 'w') as f:
                f.write(content)

        # Create ZIP file
        zip_filename = f"{user_data['church_name']}_Documents_{timestamp}.zip".replace(' ', '_')
        zip_path = os.path.join(UPLOAD_FOLDER, zip_filename)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename in os.listdir(church_folder):
                file_path = os.path.join(church_folder, filename)
                zipf.write(file_path, filename)

        # Email documents (if configured)
        try:
            send_documents_email(
                to_email=user_data['email'],
                church_name=user_data['church_name'],
                zip_path=zip_path,
                zip_filename=zip_filename
            )
            email_sent = True
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            email_sent = False

        return jsonify({
            'success': True,
            'message': 'Documents generated successfully',
            'email_sent': email_sent,
            'download_url': f'/download/{zip_filename}'
        })

    except Exception as e:
        print(f"Error generating documents: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Allow document download"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404

@app.route('/documents-generated')
def success_page():
    """Success page after generation"""
    email = request.args.get('email', '')

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Documents Generated Successfully!</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Georgia', serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
                color: #333;
                line-height: 1.6;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .success-card {{
                background: white;
                border-radius: 12px;
                padding: 60px 40px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                max-width: 600px;
                text-align: center;
            }}

            .checkmark {{
                width: 80px;
                height: 80px;
                border-radius: 50%;
                background: #28a745;
                color: white;
                font-size: 48px;
                line-height: 80px;
                margin: 0 auto 30px;
            }}

            h1 {{
                color: #0f3460;
                margin-bottom: 20px;
                font-size: 2em;
            }}

            p {{
                color: #666;
                margin-bottom: 15px;
                font-size: 1.1em;
            }}

            .email {{
                color: #0f3460;
                font-weight: 600;
            }}

            .next-steps {{
                background: #f8f9fa;
                border-radius: 8px;
                padding: 30px;
                margin: 30px 0;
                text-align: left;
            }}

            .next-steps h2 {{
                color: #0f3460;
                margin-bottom: 20px;
                font-size: 1.5em;
            }}

            .next-steps ol {{
                margin-left: 20px;
            }}

            .next-steps li {{
                margin-bottom: 15px;
                color: #333;
            }}

            .disclaimer {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin-top: 30px;
                text-align: left;
                font-size: 0.95em;
            }}

            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
                color: white;
                padding: 14px 40px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: 600;
                margin-top: 20px;
                transition: transform 0.3s;
            }}

            .btn:hover {{
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="success-card">
            <div class="checkmark">✓</div>

            <h1>Documents Generated Successfully!</h1>

            <p>Your customized church formation documents have been generated and sent to:</p>
            <p class="email">{email}</p>

            <div class="next-steps">
                <h2>📋 Next Steps:</h2>
                <ol>
                    <li><strong>Check your email</strong> - You should receive your documents within 5 minutes (check spam folder if needed)</li>
                    <li><strong>Review all documents carefully</strong> - Make sure they accurately reflect your church's beliefs and structure</li>
                    <li><strong>Consult with an attorney</strong> - Have a qualified attorney licensed in your state review these documents before using them</li>
                    <li><strong>Customize as needed</strong> - Work with your attorney to make any necessary modifications</li>
                    <li><strong>Implement your governance</strong> - Once finalized, begin using these documents to guide your church operations</li>
                    <li><strong>Maintain good records</strong> - Follow the recordkeeping guidelines provided</li>
                </ol>
            </div>

            <div class="disclaimer">
                <strong>⚠️ IMPORTANT REMINDER:</strong><br>
                These documents are educational templates generated by AI based on your input. They have NOT been reviewed by an attorney. Before using these documents, you MUST consult with a qualified attorney licensed in your state to ensure they meet all legal requirements and are appropriate for your specific situation.
            </div>

            <a href="/" class="btn">← Back to Home</a>
        </div>
    </body>
    </html>
    """

    return html

def send_documents_email(to_email: str, church_name: str, zip_path: str, zip_filename: str):
    """
    Send generated documents via email
    NOTE: This requires SMTP configuration
    """

    # SMTP configuration (would need to be set up)
    # For now, this is a placeholder showing the structure
    # In production, use SendGrid, Mailgun, or similar service

    """
    Example SMTP setup (uncomment and configure when ready):

    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "noreply@churchformation.com"
    sender_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = f"Your Church Formation Documents - {church_name}"

    body = f'''
    Dear {church_name} Leadership,

    Your customized church formation documents have been generated!

    Please find attached a ZIP file containing all your documents:
    - Articles of Faith
    - Church Bylaws
    - IRS Letter 1045 Template
    - Operating Procedures
    - Meeting Minutes Template
    - Recordkeeping Guidelines

    IMPORTANT REMINDER:
    These documents are educational templates generated based on your input.
    They have NOT been reviewed by an attorney. Before using these documents,
    you MUST consult with a qualified attorney licensed in your state.

    Next Steps:
    1. Review all documents carefully
    2. Consult with a qualified attorney
    3. Customize as needed with attorney guidance
    4. Begin implementing your church governance

    Questions? Reply to this email.

    Blessings,
    The Church Formation Guidance Team

    ---
    DISCLAIMER: Educational information only. Not legal advice.
    '''

    msg.attach(MIMEText(body, 'plain'))

    # Attach ZIP file
    with open(zip_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={zip_filename}')
    msg.attach(part)

    # Send email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
    """

    # For now, just log that we would send email
    print(f"✉️  Would send email to: {to_email}")
    print(f"📎 Attachment: {zip_filename}")

    # Raise exception so caller knows email wasn't actually sent
    raise Exception("SMTP not configured - email not sent (but documents generated)")

if __name__ == '__main__':
    print("🚀 Starting Church Formation Guidance Service...")
    print("📍 Running on http://localhost:5000")
    print("💡 Access the questionnaire at: http://localhost:5000/get-started")
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)
