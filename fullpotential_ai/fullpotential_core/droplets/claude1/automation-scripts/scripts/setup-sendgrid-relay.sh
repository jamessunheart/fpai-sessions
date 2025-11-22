#!/bin/bash
# setup-sendgrid-relay.sh - Easy email relay setup (no Gmail password needed)

set -e

echo "📧 Email Relay Setup - No Gmail Password Required!"
echo ""
echo "We'll use SendGrid (free tier: 100 emails/day) to relay emails."
echo "This means your daily reports WILL reach Gmail without any Gmail password."
echo ""

# Instructions for user
cat << 'INSTRUCTIONS'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK SETUP (5 minutes):

1. Sign up for SendGrid (FREE):
   https://signup.sendgrid.com/

2. After signing up:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name: "FullPotential Mail"
   - Permissions: "Full Access" or "Mail Send"
   - Click "Create & View"
   - COPY the API key (it only shows once!)

3. Verify sender email:
   - Go to Settings → Sender Authentication
   - Click "Verify a Single Sender"
   - Use: james@fullpotential.com or reports@fullpotential.com
   - Check your email dashboard for verification link

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTRUCTIONS

read -p "Press ENTER after you have your SendGrid API key ready..."

echo ""
read -p "Paste your SendGrid API key: " SENDGRID_API_KEY

if [ -z "$SENDGRID_API_KEY" ]; then
    echo "❌ API key required"
    exit 1
fi

echo ""
echo "🔧 Configuring Postfix to use SendGrid..."

# Configure Postfix on server
ssh root@198.54.123.234 << EOF
# Create SASL password file
cat > /etc/postfix/sasl_passwd << SASL_EOF
[smtp.sendgrid.net]:587 apikey:${SENDGRID_API_KEY}
SASL_EOF

# Secure the file
chmod 600 /etc/postfix/sasl_passwd
postmap /etc/postfix/sasl_passwd

# Configure Postfix
postconf -e 'relayhost = [smtp.sendgrid.net]:587'
postconf -e 'smtp_sasl_auth_enable = yes'
postconf -e 'smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd'
postconf -e 'smtp_sasl_security_options = noanonymous'
postconf -e 'smtp_tls_security_level = encrypt'
postconf -e 'header_size_limit = 4096000'

# Restart Postfix
systemctl restart postfix

echo "✅ Postfix configured to use SendGrid!"
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ SETUP COMPLETE!"
echo ""
echo "🧪 Sending test email..."

# Send test email
ssh root@198.54.123.234 << 'TEST_EOF'
echo "This is a test email sent via SendGrid!

If you receive this in your Gmail, the setup is complete and working perfectly.

Daily session summaries will now arrive at:
- Email Dashboard: http://198.54.123.234:8030
- Gmail: james.rick.stinson@gmail.com

No Gmail password needed! 🎉

-FPAI Email System" | mail -s "✅ SendGrid Relay Active - Test Email" james@fullpotential.com
TEST_EOF

echo ""
echo "✅ Test email sent!"
echo ""
echo "Check your Gmail (james.rick.stinson@gmail.com) in 1-2 minutes."
echo ""
echo "Daily reports will now arrive automatically at 11:59 PM! 📧"
echo ""
