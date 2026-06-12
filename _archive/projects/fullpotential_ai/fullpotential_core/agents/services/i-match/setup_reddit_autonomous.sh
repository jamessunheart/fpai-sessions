#!/bin/bash
# Autonomous Reddit Setup - One-time configuration

echo "🚀 REDDIT AUTONOMOUS POSTING SETUP"
echo "=================================="
echo ""
echo "Reddit app page is now open in your browser."
echo ""
echo "QUICK SETUP (2 minutes):"
echo ""
echo "1. On the Reddit page, scroll to bottom"
echo "2. Click 'create another app' or 'create app'"
echo "3. Fill in:"
echo "   Name: I-MATCH-Bot"
echo "   Type: script"
echo "   Description: Financial advisor matching automation"
echo "   Redirect URI: http://localhost:8080"
echo "4. Click 'create app'"
echo ""
echo "5. Copy the credentials:"
read -p "   Reddit Client ID (under app name): " REDDIT_CLIENT_ID
read -p "   Reddit Client Secret: " REDDIT_CLIENT_SECRET
read -p "   Your Reddit Username: " REDDIT_USERNAME
read -sp "   Your Reddit Password: " REDDIT_PASSWORD
echo ""
echo ""

# Save to credential vault
cd /Users/jamessunheart/Development/docs/coordination/scripts

echo "Saving to credential vault..."
./session-set-credential.sh reddit_client_id "$REDDIT_CLIENT_ID" api_key reddit
./session-set-credential.sh reddit_client_secret "$REDDIT_CLIENT_SECRET" api_key reddit  
./session-set-credential.sh reddit_username "$REDDIT_USERNAME" username reddit
./session-set-credential.sh reddit_password "$REDDIT_PASSWORD" password reddit

echo ""
echo "✅ Reddit credentials saved!"
echo ""
echo "Now installing Reddit API library..."
pip3 install praw >/dev/null 2>&1

echo ""
echo "🎉 SETUP COMPLETE!"
echo ""
echo "Autonomous posting is now active. Run:"
echo "  python3 /Users/jamessunheart/Development/agents/services/i-match/reddit_autonomous_post.py"
echo ""
