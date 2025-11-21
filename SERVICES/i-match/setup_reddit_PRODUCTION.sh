#!/bin/bash
# Production Reddit Setup - Using fullpotential.com

echo "🚀 REDDIT PRODUCTION SETUP"
echo "=========================================="
echo ""
echo "✅ USING PRODUCTION DOMAIN: fullpotential.com"
echo ""
echo "In the Reddit app page that just opened:"
echo ""
echo "1. Click 'create another app'"
echo "2. Fill in:"
echo "   Name: I-MATCH-Financial-Advisor-Bot"
echo "   Type: web app"
echo "   About URL: https://fullpotential.com"
echo "   Redirect URI: https://fullpotential.com/api/reddit/callback"
echo "3. Click 'create app'"
echo ""
echo "4. Enter credentials below:"
echo ""
read -p "Reddit Client ID: " CLIENT_ID
read -p "Reddit Client Secret: " CLIENT_SECRET
read -p "Reddit Username: " USERNAME
read -sp "Reddit Password: " PASSWORD
echo ""

# Save to vault
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-set-credential.sh reddit_client_id "$CLIENT_ID" api_key reddit
./session-set-credential.sh reddit_client_secret "$CLIENT_SECRET" api_key reddit
./session-set-credential.sh reddit_username "$USERNAME" username reddit
./session-set-credential.sh reddit_password "$PASSWORD" password reddit

echo ""
echo "✅ Credentials saved!"
echo ""
echo "Installing praw..."
pip3 install -q praw

echo ""
echo "🎉 PRODUCTION REDDIT POSTING READY!"
echo ""
echo "Test it:"
echo "  python3 /Users/jamessunheart/Development/SERVICES/i-match/reddit_autonomous_post.py"
