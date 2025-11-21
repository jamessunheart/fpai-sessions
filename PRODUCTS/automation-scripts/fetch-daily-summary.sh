#!/bin/bash
# fetch-daily-summary.sh - Fetch daily summary from server

set -e

SERVER="root@198.54.123.234"
SERVER_BASE="/root/coordination"
DATE=${1:-$(date +%Y-%m-%d)}
LOCAL_DIR="/Users/jamessunheart/Development/docs/coordination/DAILY_SUMMARIES"

echo "📥 Fetching daily summary from server..."
echo "   Date: $DATE"

# Create local directory
mkdir -p "$LOCAL_DIR"

# Fetch summary
REMOTE_FILE="$SERVER_BASE/DAILY_SUMMARIES/daily-summary-$DATE.md"
LOCAL_FILE="$LOCAL_DIR/daily-summary-$DATE.md"

if scp "$SERVER:$REMOTE_FILE" "$LOCAL_FILE" 2>/dev/null; then
    echo "✅ Summary fetched successfully!"
    echo ""
    echo "📖 View summary:"
    echo "   cat $LOCAL_FILE"
    echo ""
    echo "📊 Quick preview:"
    echo ""
    head -50 "$LOCAL_FILE"
else
    echo "❌ Summary not found for $DATE"
    echo ""
    echo "📁 Available summaries on server:"
    ssh $SERVER "ls -1 $SERVER_BASE/DAILY_SUMMARIES/ | tail -10"
    echo ""
    echo "💡 To fetch a different date:"
    echo "   ./fetch-daily-summary.sh 2025-11-14"
fi
