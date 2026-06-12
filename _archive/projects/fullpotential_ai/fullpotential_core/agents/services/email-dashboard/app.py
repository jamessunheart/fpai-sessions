#!/usr/bin/env python3
"""Email Dashboard for james@fullpotential.com"""

from flask import Flask, render_template, jsonify
import mailbox
import email
from email.utils import parsedate_to_datetime
from datetime import datetime
import os

app = Flask(__name__)

MAILDIR_PATH = "/home/james/Maildir"

def get_emails(folder='new', limit=50):
    """Read emails from Maildir"""
    emails = []
    maildir = mailbox.Maildir(MAILDIR_PATH)
    
    # Get folder (new, cur, or all)
    if folder == 'new':
        messages = [(key, maildir[key]) for key in maildir.keys() if maildir.get_folder('new')]
    else:
        messages = [(key, maildir[key]) for key in maildir.keys()]
    
    # Sort by date (newest first)
    messages.sort(key=lambda x: x[1].get('Date', ''), reverse=True)
    
    for key, msg in messages[:limit]:
        try:
            # Parse date
            date_str = msg.get('Date', '')
            try:
                date = parsedate_to_datetime(date_str)
            except:
                date = None
            
            # Get body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            emails.append({
                'id': key,
                'from': msg.get('From', 'Unknown'),
                'to': msg.get('To', ''),
                'subject': msg.get('Subject', '(No Subject)'),
                'date': date.strftime('%Y-%m-%d %H:%M:%S') if date else 'Unknown',
                'body': body[:500] + ('...' if len(body) > 500 else ''),
                'full_body': body,
                'size': len(str(msg))
            })
        except Exception as e:
            print(f"Error parsing email {key}: {e}")
            continue
    
    return emails

@app.route('/')
def index():
    """Main dashboard"""
    emails = get_emails(folder='all', limit=50)
    
    return render_template('index.html',
                         emails=emails,
                         total_count=len(emails),
                         email_address='james@fullpotential.com',
                         forward_to='james.rick.stinson@gmail.com')

@app.route('/api/emails')
def api_emails():
    """API endpoint for emails"""
    emails = get_emails(folder='all', limit=100)
    return jsonify(emails)

@app.route('/api/email/<email_id>')
def api_email(email_id):
    """Get single email details"""
    emails = get_emails(folder='all')
    for email in emails:
        if email['id'] == email_id:
            return jsonify(email)
    return jsonify({'error': 'Email not found'}), 404

@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'service': 'email-dashboard'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8030, debug=False)
