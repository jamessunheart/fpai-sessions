#!/bin/bash
# Setup API credentials for autonomous campaign bot

echo "=================================================="
echo "🔐 API CREDENTIALS SETUP"
echo "=================================================="
echo ""
echo "This script helps you configure API credentials"
echo "for the autonomous campaign bot."
echo ""
echo "The bot will then run 24/7, posting and responding"
echo "automatically to get the first SOL."
echo ""

ENV_FILE="/Users/jamessunheart/Development/docs/coordination/.env.campaign"

# Create .env file if it doesn't exist
touch "$ENV_FILE"

echo "Let's set up your API credentials..."
echo ""

# === REDDIT ===
echo "📱 REDDIT API CREDENTIALS"
echo "Get these from: https://www.reddit.com/prefs/apps"
echo ""

read -p "Reddit Client ID (or press Enter to skip): " REDDIT_CLIENT_ID
read -p "Reddit Client Secret: " REDDIT_CLIENT_SECRET
read -p "Reddit Username: " REDDIT_USERNAME
read -sp "Reddit Password: " REDDIT_PASSWORD
echo ""

if [ -n "$REDDIT_CLIENT_ID" ]; then
    cat >> "$ENV_FILE" << EOF
# Reddit API
REDDIT_CLIENT_ID=$REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET=$REDDIT_CLIENT_SECRET
REDDIT_USERNAME=$REDDIT_USERNAME
REDDIT_PASSWORD=$REDDIT_PASSWORD

EOF
    echo "✅ Reddit credentials saved"
else
    echo "⏭️  Skipped Reddit setup"
fi

echo ""

# === TWITTER ===
echo "🐦 TWITTER (X) API CREDENTIALS"
echo "Get these from: https://developer.twitter.com/en/portal/dashboard"
echo ""

read -p "Twitter API Key (or press Enter to skip): " TWITTER_API_KEY
read -p "Twitter API Secret: " TWITTER_API_SECRET
read -p "Twitter Access Token: " TWITTER_ACCESS_TOKEN
read -p "Twitter Access Secret: " TWITTER_ACCESS_SECRET

if [ -n "$TWITTER_API_KEY" ]; then
    cat >> "$ENV_FILE" << EOF
# Twitter API
TWITTER_API_KEY=$TWITTER_API_KEY
TWITTER_API_SECRET=$TWITTER_API_SECRET
TWITTER_ACCESS_TOKEN=$TWITTER_ACCESS_TOKEN
TWITTER_ACCESS_SECRET=$TWITTER_ACCESS_SECRET

EOF
    echo "✅ Twitter credentials saved"
else
    echo "⏭️  Skipped Twitter setup"
fi

echo ""

# === DISCORD ===
echo "💬 DISCORD BOT TOKEN"
echo "Get this from: https://discord.com/developers/applications"
echo ""

read -p "Discord Bot Token (or press Enter to skip): " DISCORD_BOT_TOKEN

if [ -n "$DISCORD_BOT_TOKEN" ]; then
    cat >> "$ENV_FILE" << EOF
# Discord Bot
DISCORD_BOT_TOKEN=$DISCORD_BOT_TOKEN

EOF
    echo "✅ Discord credentials saved"
else
    echo "⏭️  Skipped Discord setup"
fi

echo ""
echo "=================================================="
echo "✅ SETUP COMPLETE"
echo "=================================================="
echo ""
echo "Credentials saved to: $ENV_FILE"
echo ""
echo "Next steps:"
echo "1. Source the credentials:"
echo "   source $ENV_FILE"
echo ""
echo "2. Install Python dependencies:"
echo "   pip install praw tweepy discord.py requests"
echo ""
echo "3. Start the autonomous bot:"
echo "   python3 autonomous-campaign-bot.py"
echo ""
echo "The bot will run 24/7, even while you sleep!"
echo ""
