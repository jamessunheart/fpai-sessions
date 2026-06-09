#!/bin/bash
###############################################################################
# ACTIVATE AUTONOMOUS EMAIL RECRUITER
# Sends personalized emails to 20 highly-qualified financial advisor prospects
# Fully autonomous - runs 24/7 without human intervention
###############################################################################

echo "════════════════════════════════════════════════════════════════════════"
echo "🤖 AUTONOMOUS EMAIL RECRUITER - ACTIVATION"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Check if SMTP credentials are set
if [[ -z "$SMTP_USER" || -z "$SMTP_PASSWORD" ]]; then
    echo "⚠️  SMTP credentials not configured"
    echo ""
    echo "To activate, you need email credentials. Choose one option:"
    echo ""
    echo "OPTION 1: Gmail (Easiest)"
    echo "  1. Go to: https://myaccount.google.com/apppasswords"
    echo "  2. Create app password for 'I MATCH Email Recruiter'"
    echo "  3. Run:"
    echo "     export SMTP_SERVER='smtp.gmail.com'"
    echo "     export SMTP_PORT='587'"
    echo "     export SMTP_USER='your-email@gmail.com'"
    echo "     export SMTP_PASSWORD='your-16-char-app-password'"
    echo "     export FROM_EMAIL='your-email@gmail.com'"
    echo "  4. Run this script again"
    echo ""
    echo "OPTION 2: Use SendGrid/Brevo API (check credential vault)"
    echo ""
    echo "OPTION 3: Simulation Mode (for testing)"
    echo "  export SIMULATION_MODE='true'"
    echo "  (Logs emails without actually sending)"
    echo ""
    exit 1
fi

cd /Users/jamessunheart/Development/SERVICES/i-match

echo "📊 Current Status:"
python3 autonomous_email_recruiter.py --stats
echo ""

echo "🚀 Ready to activate autonomous email recruitment!"
echo ""
echo "This will:"
echo "  • Send personalized emails to 20 financial advisor prospects"
echo "  • Rate: 10 emails/hour (professional, not spam)"
echo "  • Timeline: All 20 contacted in 2 hours"
echo "  • Expected: 1-3 responses within 24 hours"
echo ""
read -p "Activate? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "✅ ACTIVATING AUTONOMOUS MODE..."
    echo ""

    # Run in background
    nohup python3 autonomous_email_recruiter.py --autonomous --rate 10 > autonomous_email.log 2>&1 &

    PID=$!
    echo "✅ Autonomous recruiter activated!"
    echo ""
    echo "Process ID: $PID"
    echo "Log file: autonomous_email.log"
    echo ""
    echo "To monitor:"
    echo "  tail -f autonomous_email.log"
    echo ""
    echo "To check stats:"
    echo "  python3 autonomous_email_recruiter.py --stats"
    echo ""
    echo "To stop:"
    echo "  kill $PID"
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    echo "🎯 EXPECTED RESULTS:"
    echo "  • 20 emails sent in 2 hours"
    echo "  • 5 opens (25% open rate) within 6 hours"
    echo "  • 1-2 responses within 24 hours"
    echo "  • 1 advisor signup within 48 hours"
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
else
    echo "❌ Activation cancelled"
fi
