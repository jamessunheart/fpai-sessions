#!/bin/bash
# setup-email-reports.sh - Setup automatic email delivery of daily summaries

set -e

SERVER="root@198.54.123.234"
SERVER_BASE="/root/coordination"

echo "📧 Setting up automatic email reports..."
echo ""

# Get user email
read -p "Enter your email address: " USER_EMAIL

if [ -z "$USER_EMAIL" ]; then
    echo "❌ Email address required"
    exit 1
fi

echo ""
echo "📝 Creating email script on server..."

# Create email script on server
ssh $SERVER "cat > $SERVER_BASE/email-summary.py" << 'REMOTE_SCRIPT'
#!/usr/bin/env python3
"""Email daily summary script"""

import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email(to_email, subject, body_text, body_html=None):
    """Send email using SMTP"""

    # Email configuration
    SMTP_SERVER = "smtp.gmail.com"  # Change if using different provider
    SMTP_PORT = 587

    # Get credentials from environment or use app-specific password
    # For Gmail: Use app-specific password from https://myaccount.google.com/apppasswords
    import os
    SMTP_USER = os.environ.get('SMTP_USER', 'your-email@gmail.com')
    SMTP_PASS = os.environ.get('SMTP_PASS', '')

    if not SMTP_PASS:
        print("⚠️  SMTP_PASS environment variable not set")
        print("Set it with: export SMTP_PASS='your-app-specific-password'")
        return False

    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    # Attach text version
    part1 = MIMEText(body_text, 'plain')
    msg.attach(part1)

    # Attach HTML version if provided
    if body_html:
        part2 = MIMEText(body_html, 'html')
        msg.attach(part2)

    try:
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        print(f"✅ Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def read_summary(date_str):
    """Read daily summary file"""
    summary_file = f"/root/coordination/DAILY_SUMMARIES/daily-summary-{date_str}.md"

    try:
        with open(summary_file, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Summary file not found: {summary_file}")
        return None

def markdown_to_html(markdown_text):
    """Simple markdown to HTML conversion"""
    import re

    html = markdown_text

    # Headers
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

    # Code blocks
    html = re.sub(r'```(.*?)```', r'<pre>\1</pre>', html, flags=re.DOTALL)
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)

    # Lists
    html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Line breaks
    html = html.replace('\n', '<br>\n')

    # Wrap in HTML
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            h3 {{ color: #7f8c8d; }}
            pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
            li {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

if __name__ == "__main__":
    # Get date (default to today)
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    to_email = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('REPORT_EMAIL')

    if not to_email:
        print("❌ Email address required")
        print("Usage: python3 email-summary.py [DATE] [EMAIL]")
        sys.exit(1)

    # Read summary
    summary_text = read_summary(date_str)
    if not summary_text:
        sys.exit(1)

    # Convert to HTML
    summary_html = markdown_to_html(summary_text)

    # Send email
    subject = f"Daily Session Summary - {date_str}"
    send_email(to_email, subject, summary_text, summary_html)
REMOTE_SCRIPT

# Make it executable
ssh $SERVER "chmod +x $SERVER_BASE/email-summary.py"

echo "   ✅ Email script created"
echo ""

# Update compression script to send email after generating summary
echo "📝 Updating compression script to send email..."

ssh $SERVER << REMOTE_UPDATE
# Add email sending to compression script
cat >> $SERVER_BASE/compress-logs.sh << 'COMPRESSION_EMAIL'

# Send email after compression
if [ -n "\$REPORT_EMAIL" ]; then
    echo ""
    echo "📧 Sending email report to \$REPORT_EMAIL..."
    /usr/bin/python3 $SERVER_BASE/email-summary.py \$DATE \$REPORT_EMAIL
fi
COMPRESSION_EMAIL

chmod +x $SERVER_BASE/compress-logs.sh
echo "✅ Compression script updated"
REMOTE_UPDATE

echo ""
echo "🔐 Setting up email credentials on server..."
echo ""
echo "You need to set up email credentials on the server:"
echo ""
echo "1. For Gmail:"
echo "   - Go to: https://myaccount.google.com/apppasswords"
echo "   - Generate an app-specific password"
echo "   - Copy the password"
echo ""
echo "2. On the server, run:"
echo "   ssh $SERVER"
echo "   export SMTP_USER='your-email@gmail.com'"
echo "   export SMTP_PASS='your-app-specific-password'"
echo "   export REPORT_EMAIL='$USER_EMAIL'"
echo ""
echo "3. Add to server's crontab environment:"
echo "   crontab -e"
echo "   # Add these lines at the top:"
echo "   SMTP_USER=your-email@gmail.com"
echo "   SMTP_PASS=your-app-specific-password"
echo "   REPORT_EMAIL=$USER_EMAIL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ EMAIL REPORTING SETUP COMPLETE!"
echo ""
echo "📧 Reports will be sent to: $USER_EMAIL"
echo ""
echo "🔧 To test now:"
echo "   ssh $SERVER"
echo "   export SMTP_USER='your-email@gmail.com'"
echo "   export SMTP_PASS='your-app-password'"
echo "   export REPORT_EMAIL='$USER_EMAIL'"
echo "   /usr/bin/python3 $SERVER_BASE/email-summary.py"
echo ""
echo "🕐 Automatic emails will be sent daily at 11:59 PM"
echo "   (after setting up credentials in crontab)"
echo ""
