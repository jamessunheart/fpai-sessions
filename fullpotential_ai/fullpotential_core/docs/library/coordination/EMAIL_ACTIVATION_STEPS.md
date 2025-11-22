# Email Reports - Activation Steps

## ✅ DEPLOYMENT COMPLETE

The automated email reporting system has been fully deployed to the server.

**What's Already Set Up:**
- ✅ `/root/coordination/email-summary.py` - Email sending script deployed
- ✅ `/root/coordination/compress-logs.sh` - Updated to send emails after compression
- ✅ Cron job running daily at 11:59 PM
- ✅ Log compression working (tested)
- ✅ Daily summaries generating properly

---

## 🔐 FINAL STEP: Configure Email Credentials

You need to add email credentials to the server's crontab environment. This is a one-time setup.

### Step 1: Generate Gmail App Password

1. Go to: https://myaccount.google.com/apppasswords
2. Select "Mail" and "Other (Custom name)"
3. Name it "FPAI Session Reports"
4. Copy the 16-character password

### Step 2: Add Credentials to Server Crontab

```bash
ssh root@198.54.123.234
crontab -e
```

Add these lines **at the very top** of the crontab file:

```bash
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-16-char-app-password
REPORT_EMAIL=your-email@gmail.com
```

**Example:**
```bash
SMTP_USER=james@gmail.com
SMTP_PASS=abcd efgh ijkl mnop
REPORT_EMAIL=james@gmail.com
```

Then the cron job line below:
```bash
59 23 * * * /root/coordination/compress-logs.sh >> /root/coordination/DAILY_SUMMARIES/cron.log 2>&1
```

Save and exit (`:wq` in vi, or `Ctrl+X` then `Y` in nano).

---

## 🧪 TEST THE EMAIL SYSTEM

After configuring credentials, test immediately:

```bash
ssh root@198.54.123.234

# Set environment variables for this session
export SMTP_USER='your-email@gmail.com'
export SMTP_PASS='your-app-password'
export REPORT_EMAIL='your-email@gmail.com'

# Test email sending
/usr/bin/python3 /root/coordination/email-summary.py

# You should receive an email with today's summary within 1-2 minutes
```

Check your inbox (and spam folder if needed).

---

## 📧 WHAT YOU'LL RECEIVE

**Every day at 11:59 PM (Server Time):**

**Subject:** Daily Session Summary - YYYY-MM-DD

**Content:**
- 🎯 System Overview (SSOT stats, server status)
- 📊 All Active Sessions' Activity
- ✅ Completed Tasks
- 🚧 Current Blockers
- 💡 Learnings from Last 24 Hours
- 📈 Metrics (sessions, tasks, blockers)

**Format:** HTML-styled email with colors, headings, and code blocks

---

## 🔍 VERIFY SETUP

Check that everything is configured:

```bash
ssh root@198.54.123.234

# 1. Verify email script exists
ls -la /root/coordination/email-summary.py

# 2. Verify compression script has email integration
tail -10 /root/coordination/compress-logs.sh

# 3. Verify cron job is scheduled
crontab -l

# 4. Check cron log for any errors
tail -20 /root/coordination/DAILY_SUMMARIES/cron.log
```

---

## 🎯 COMPLETE AUTOMATED WORKFLOW

```
Daily at 11:59 PM (Server Time)
       ↓
1. Cron triggers /root/coordination/compress-logs.sh
       ↓
2. Script scans all session logs in /root/coordination/sessions/ACTIVE/
       ↓
3. Generates daily summary markdown file
       ↓
4. Reads SSOT.json for system overview
       ↓
5. Creates comprehensive daily summary
       ↓
6. Saves to /root/coordination/DAILY_SUMMARIES/daily-summary-YYYY-MM-DD.md
       ↓
7. Calls email-summary.py with date and email
       ↓
8. email-summary.py converts markdown to HTML
       ↓
9. Sends email via Gmail SMTP
       ↓
10. You receive summary in inbox
       ↓
✅ Complete visibility, zero manual action
```

---

## 📚 FULL DOCUMENTATION

For detailed information, see:
- `/Users/jamessunheart/Development/docs/coordination/EMAIL_REPORTS_GUIDE.md`

For troubleshooting and customization options.

---

## 🎉 NEXT AUTOMATIC EMAIL

Once you configure the credentials, your next email will arrive:
- **Tomorrow at 11:59 PM** (if configured before then)
- **Or test now** using the test command above

**Status:** Ready to activate - just add credentials! 🚀
