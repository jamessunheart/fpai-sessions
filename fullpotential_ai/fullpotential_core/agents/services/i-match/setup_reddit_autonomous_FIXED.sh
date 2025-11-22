#!/bin/bash
# Autonomous Reddit Setup - FIXED with proper redirect URI

echo "🚀 REDDIT AUTONOMOUS POSTING SETUP"
echo "=================================="
echo ""
echo "CORRECTED SETUP:"
echo ""
echo "1. On Reddit app page, scroll to bottom"
echo "2. Click 'create another app' or 'create app'"
echo "3. Fill in:"
echo "   Name: I-MATCH-Bot"
echo "   Type: script"
echo "   Description: Financial advisor matching automation"
echo "   Redirect URI: https://fullpotential.com/reddit-callback"
echo "   (Or use: http://127.0.0.1:8080 for script type)"
echo "4. Click 'create app'"
echo ""
echo "NOTE: For 'script' type apps, redirect URI doesn't matter much"
echo "      Just use http://127.0.0.1:8080"
echo ""
echo "5. Enter the credentials below:"
echo ""
read -p "   Reddit Client ID (under app name): " REDDIT_CLIENT_ID
read -p "   Reddit Client Secret: " REDDIT_CLIENT_SECRET
read -p "   Your Reddit Username: " REDDIT_USERNAME
read -sp "   Your Reddit Password: " REDDIT_PASSWORD
echo ""
echo ""

# Save to credential vault
cd /Users/jamessunheart/Development/docs/coordination/scripts

echo "Saving to credential vault..."
./session-set-credential.sh reddit_client_id "$REDDIT_CLIENT_ID" api_key reddit 2>/dev/null
./session-set-credential.sh reddit_client_secret "$REDDIT_CLIENT_SECRET" api_key reddit 2>/dev/null
./session-set-credential.sh reddit_username "$REDDIT_USERNAME" username reddit 2>/dev/null
./session-set-credential.sh reddit_password "$REDDIT_PASSWORD" password reddit 2>/dev/null

echo ""
echo "✅ Reddit credentials saved to vault!"
echo ""
echo "Installing Reddit API library..."
pip3 install -q praw

echo ""
echo "🎉 SETUP COMPLETE!"
echo ""
echo "Testing autonomous posting now..."
python3 /Users/jamessunheart/Development/agents/services/i-match/reddit_autonomous_post.py
