#!/bin/bash
# While You Sleep - Start autonomous campaign that runs 24/7

SCRIPT_DIR="/Users/jamessunheart/Development/docs/coordination/scripts"
ENV_FILE="$SCRIPT_DIR/.env.campaign"
PID_FILE="$SCRIPT_DIR/campaign-bot.pid"
LOG_FILE="/Users/jamessunheart/Development/docs/coordination/outreach/campaign_log.txt"

echo "=================================================="
echo "😴 WHILE YOU SLEEP - Autonomous Campaign"
echo "=================================================="
echo ""

# Check if bot is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Campaign bot is already running (PID: $PID)"
        echo ""
        echo "View logs:"
        echo "  tail -f $LOG_FILE"
        echo ""
        echo "Stop bot:"
        echo "  kill $PID"
        echo "  rm $PID_FILE"
        exit 0
    else
        echo "🔄 Stale PID file found, removing..."
        rm "$PID_FILE"
    fi
fi

# Check for API credentials
if [ -f "$ENV_FILE" ]; then
    echo "✅ API credentials found"
    source "$ENV_FILE"
else
    echo "⚠️  No API credentials configured yet"
    echo ""
    echo "The bot will run in monitor-only mode."
    echo "It will watch for SOL and log activity, but won't post automatically."
    echo ""
    echo "To enable full automation, run:"
    echo "  bash setup-api-credentials.sh"
    echo ""
    read -p "Continue in monitor-only mode? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install dependencies if needed
echo ""
echo "📦 Checking Python dependencies..."
pip3 install -q -r "$SCRIPT_DIR/requirements-campaign.txt" 2>&1 | grep -v "already satisfied" || true
echo "✅ Dependencies ready"

# Start the bot in background
echo ""
echo "🚀 Starting autonomous campaign bot..."
cd "$SCRIPT_DIR"

nohup python3 autonomous-campaign-bot.py > /dev/null 2>&1 &
BOT_PID=$!

# Save PID
echo $BOT_PID > "$PID_FILE"

# Wait a moment to check if it started successfully
sleep 2

if ps -p $BOT_PID > /dev/null; then
    echo "✅ Bot started successfully!"
    echo ""
    echo "=================================================="
    echo "🌙 RUNNING WHILE YOU SLEEP"
    echo "=================================================="
    echo ""
    echo "PID: $BOT_PID"
    echo "Log: $LOG_FILE"
    echo ""
    echo "What the bot is doing:"
    echo "  ✅ Monitoring church wallet every 30 seconds"
    echo "  ✅ Watching for first SOL transaction"
    echo "  ✅ Will auto-post celebration when SOL arrives"
    echo "  ✅ Will post milestone updates (2, 5, 10, 25, 50, 100 supporters)"
    echo "  ✅ Continuously optimizing campaign"
    echo ""
    echo "View live logs:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "Stop the bot:"
    echo "  kill $BOT_PID"
    echo "  rm $PID_FILE"
    echo ""
    echo "The bot will keep running even if you close this terminal."
    echo ""
    echo "😴 Go to sleep! The bot has this covered. 🤖"
    echo "=================================================="
else
    echo "❌ Bot failed to start"
    rm "$PID_FILE"
    exit 1
fi
