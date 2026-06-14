#!/bin/bash

# Start SSOT Service - Background process that keeps SSOT updated

SSOT_DIR="/Users/jamessunheart/Development/docs/coordination"
SSOT_PID_FILE="$SSOT_DIR/.ssot-watcher.pid"
SSOT_LOG_FILE="$SSOT_DIR/ssot-watcher.log"

# Check if already running
if [ -f "$SSOT_PID_FILE" ]; then
    OLD_PID=$(cat "$SSOT_PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  SSOT watcher already running (PID: $OLD_PID)"
        echo "   To stop: kill $OLD_PID"
        exit 1
    fi
fi

echo "🚀 Starting SSOT Background Service..."
echo ""

# Start the watcher in background
cd /Users/jamessunheart/Development

nohup ./docs/coordination/scripts/ssot-watcher.sh > "$SSOT_LOG_FILE" 2>&1 &
PID=$!

echo $PID > "$SSOT_PID_FILE"

echo "✅ SSOT Service started!"
echo "   PID: $PID"
echo "   Log: $SSOT_LOG_FILE"
echo "   Updates: Every 5 seconds"
echo ""
echo "📊 To view updates:"
echo "   tail -f $SSOT_LOG_FILE"
echo ""
echo "⏹️  To stop:"
echo "   kill $PID"
echo "   rm $SSOT_PID_FILE"
echo ""

# Give it a moment to start
sleep 2

# Show first update
if [ -f "$SSOT_LOG_FILE" ]; then
    echo "📝 First update:"
    tail -3 "$SSOT_LOG_FILE"
fi

echo ""
echo "🎯 SSOT is now auto-updating!"
