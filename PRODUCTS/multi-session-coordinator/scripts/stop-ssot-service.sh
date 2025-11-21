#!/bin/bash

# Stop SSOT Service

SSOT_DIR="/Users/jamessunheart/Development/docs/coordination"
SSOT_PID_FILE="$SSOT_DIR/.ssot-watcher.pid"

if [ ! -f "$SSOT_PID_FILE" ]; then
    echo "⚠️  No SSOT service running (PID file not found)"
    exit 0
fi

PID=$(cat "$SSOT_PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "⏹️  Stopping SSOT service (PID: $PID)..."
    kill "$PID"
    rm "$SSOT_PID_FILE"
    echo "✅ SSOT service stopped"
else
    echo "⚠️  Process $PID not running (cleaning up PID file)"
    rm "$SSOT_PID_FILE"
fi
