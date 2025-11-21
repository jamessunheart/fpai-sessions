# Email Reports Guide

**Automatically receive daily session summaries via email**

---

## 🎯 What You Get

Every day at 11:59 PM (after log compression), you'll receive an email with:
- System overview (SSOT stats, server status)
- All active sessions' activity
- Completed tasks across all sessions
- Current blockers
- Collective learnings from the last 24 hours
- Metrics (active sessions, tasks completed, blockers)

**One email = Complete visibility into all Claude sessions**

---

## ⚙️ One-Time Setup

### Step 1: Run Setup Script

```bash
cd docs/coordination/scripts
./setup-email-reports.sh
```

This will:
- Ask for your email address
- Create email script on server
- Update compression script to send emails

### Step 2: Configure Email Credentials

#### For Gmail (Recommended):

1. **Generate App-Specific Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Session Reports"
   - Copy the 16-character password

2. **Set Environment Variables on Server:**
   ```bash
   ssh root@198.54.123.234

   # Add to crontab environment
   crontab -e

   # Add these lines at the TOP:
   SMTP_USER=your-email@gmail.com
   SMTP_PASS=your-16-char-app-password
   REPORT_EMAIL=recipient@example.com

   # Save and exit
   ```

#### For Other Email Providers:

Edit `/root/coordination/email-summary.py` on server:
```python
# Change these lines:
SMTP_SERVER = "smtp.gmail.com"  # Change to your SMTP server
SMTP_PORT = 587                  # Change to your SMTP port
```

Common SMTP settings:
- **Gmail:** smtp.gmail.com:587
- **Outlook:** smtp-mail.outlook.com:587
- **Yahoo:** smtp.mail.yahoo.com:587
- **Custom:** Your organization's SMTP server

---

## 🧪 Testing

### Test Email Sending:

```bash
# SSH to server
ssh root@198.54.123.234

# Set environment variables (for this session)
export SMTP_USER='your-email@gmail.com'
export SMTP_PASS='your-app-password'
export REPORT_EMAIL='recipient@example.com'

# Test email script
python3 /root/coordination/email-summary.py

# You should receive an email with today's summary
```

---

## 📧 Email Format

**Subject:** Daily Session Summary - 2025-11-16

**Body:** HTML formatted with:
- Styled headers
- Color-coded sections
- Easy-to-read metrics
- Full summary content
- Direct copy from daily summary

**Attachments:** None (summary is in email body)

---

## 🔧 Customization

### Change Email Schedule

Edit server crontab:
```bash
ssh root@198.54.123.234
crontab -e

# Change from 11:59 PM to 8:00 AM:
# 59 23 * * * /root/coordination/compress-logs.sh >> /root/coordination/DAILY_SUMMARIES/cron.log 2>&1
0 8 * * * /root/coordination/compress-logs.sh >> /root/coordination/DAILY_SUMMARIES/cron.log 2>&1
```

### Add Multiple Recipients

Edit `/root/coordination/email-summary.py`:
```python
# Change this line:
to_email = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('REPORT_EMAIL')

# To send to multiple emails:
to_emails = ['email1@example.com', 'email2@example.com', 'email3@example.com']
for email in to_emails:
    send_email(email, subject, body_text, body_html)
```

### Customize Email Template

Edit `/root/coordination/email-summary.py`:
```python
def markdown_to_html(markdown_text):
    # Modify CSS styles here
    html = f"""
    <html>
    <head>
        <style>
            /* Add your custom styles */
            body {{
                font-family: Arial, sans-serif;
                background-color: #f0f0f0;  /* Change background */
            }}
            h1 {{
                color: #2c3e50;
                /* Add your styles */
            }}
        </style>
    </head>
    ...
```

---

## 🔍 Troubleshooting

### "Email not received"

1. **Check spam folder**
2. **Verify credentials:**
   ```bash
   ssh root@198.54.123.234
   crontab -l | head -5
   # Should show SMTP_USER, SMTP_PASS, REPORT_EMAIL
   ```
3. **Check cron log:**
   ```bash
   ssh root@198.54.123.234
   cat /root/coordination/DAILY_SUMMARIES/cron.log
   ```

### "Authentication failed"

- Gmail: Make sure you're using an app-specific password, not your account password
- Enable "Less secure app access" if required (not recommended)
- Check SMTP server and port settings

### "Email sent but no attachment"

- Summary is in email body, not as attachment
- Check HTML rendering in your email client
- Some email clients may block HTML formatting

---

## 📋 Complete Workflow

**Daily Automated Flow:**

```
11:59 PM (Server Time)
       ↓
Cron triggers compression script
       ↓
Compression script runs
  → Scans all session logs
  → Generates daily summary
       ↓
Email script runs
  → Reads daily summary
  → Converts to HTML
  → Sends via SMTP
       ↓
You receive email
  → Read summary in inbox
  → No need to fetch from server
  → Complete visibility
```

---

## 🎯 Benefits

✅ **Automatic** - Emails sent every day
✅ **No manual fetch** - Arrives in your inbox
✅ **HTML formatted** - Easy to read
✅ **Complete summary** - All sessions in one email
✅ **Historical** - Email archive serves as backup
✅ **Mobile friendly** - Read on any device

---

## 🔐 Security Notes

- **App-specific passwords** are safer than account passwords
- **Environment variables** keep credentials out of code
- **SMTP over TLS** encrypts email transmission
- **No credentials in crontab** visible to other users

---

## 📊 Email Example

**Subject:** Daily Session Summary - 2025-11-16

```
Daily Summary - 2025-11-16

Generated: 2025-11-16 00:04:38 (Server Time)
Active Sessions: 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM OVERVIEW

System State:
{
  "session_count": {
    "total_processes": 13,
    "registered": 23,
    "active": 3,
    "idle": 10
  },
  "server_status": { ... }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SESSION ACTIVITY

session-1
Role: Builder
Goal: AI Marketing Engine
Status: Active

Current Work:
  Working on: Email automation service
  Status: Testing
  Progress: 85%

Completed Today:
  ✓ Completed email service core functionality
  ✓ Wrote 15 tests (85% coverage)
  ✓ Deployed to staging

Blockers:
  - Waiting for SMTP credentials

---

[More sessions...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEARNINGS (Last 24 Hours)

Learning: Using asyncio.gather() speeds up parallel API calls by 10x
Impact: High
Category: Performance

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METRICS

- Active Sessions: 3
- Tasks Completed Today: 12
- Current Blockers: 2
```

---

**Wake up to a complete summary of all Claude sessions in your inbox!** 📧
