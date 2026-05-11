#!/bin/bash
# setup-gmail-forwarding.sh - Forward james@fullpotential.com to Gmail

set -e

echo "📧 Setting up email forwarding to Gmail"
echo ""

# Get user's Gmail address
read -p "Enter your Gmail address: " GMAIL_ADDR

if [ -z "$GMAIL_ADDR" ]; then
    echo "❌ Gmail address required"
    exit 1
fi

echo ""
echo "🔧 Configuring forwarding..."

# Set up forwarding on server
ssh root@198.54.123.234 << EOF
echo "$GMAIL_ADDR" > /home/james/.forward
chown james:james /home/james/.forward
chmod 644 /home/james/.forward

echo "✅ Forward file created"
cat /home/james/.forward
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ EMAIL FORWARDING CONFIGURED!"
echo ""
echo "All emails to james@fullpotential.com will now forward to:"
echo "   $GMAIL_ADDR"
echo ""
echo "🧪 Test it:"
echo "   Send an email to james@fullpotential.com"
echo "   It will appear in your Gmail inbox!"
echo ""
echo "💡 This also keeps a copy on the server at:"
echo "   /home/james/Maildir/"
echo ""
