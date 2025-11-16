from flask import Flask, render_template_string, request
import os
import email
from email.header import decode_header
from datetime import datetime

app = Flask(__name__)

MAILDIR = '/home/james/Maildir/new'

def get_emails():
    emails = []
    if os.path.exists(MAILDIR):
        for filename in sorted(os.listdir(MAILDIR), reverse=True)[:20]:
            filepath = os.path.join(MAILDIR, filename)
            with open(filepath, 'rb') as f:
                msg = email.message_from_binary_file(f)
                
                subject = str(msg.get('Subject', 'No Subject'))
                from_addr = str(msg.get('From', 'Unknown'))
                date = str(msg.get('Date', 'Unknown'))
                
                body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                emails.append({
                    'subject': subject,
                    'from': from_addr,
                    'date': date,
                    'body': body[:500]
                })
    return emails

@app.route('/')
def inbox():
    emails = get_emails()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>james@fullpotential.com - Inbox</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            h1 { color: #333; }
            .email { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
            .subject { font-weight: bold; font-size: 16px; margin-bottom: 5px; }
            .meta { color: #666; font-size: 12px; margin-bottom: 10px; }
            .body { color: #333; white-space: pre-wrap; }
            .count { color: #4CAF50; }
        </style>
    </head>
    <body>
        <h1>📧 james@fullpotential.com</h1>
        <p>Inbox: <span class=count>{{ emails|length }} messages</span></p>
        
        {% for email in emails %}
        <div class=email>
            <div class=subject>{{ email.subject }}</div>
            <div class=meta>From: {{ email.from }} | {{ email.date }}</div>
            <div class=body>{{ email.body }}</div>
        </div>
        {% endfor %}
        
        {% if not emails %}
        <p>No messages in inbox.</p>
        {% endif %}
    </body>
    </html>
    '''
    
    return render_template_string(html, emails=emails)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8032)
