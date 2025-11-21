#!/bin/bash

# 🚀 Auto-Initialize FPAI Session
# Run this automatically when Claude Code starts to register and sync

COORD_DIR="/Users/jamessunheart/Development/docs/coordination"

echo "🤖 FPAI Session Auto-Initialization"
echo ""

# Check if session is already registered
if [ -f "$COORD_DIR/.current_session" ]; then
    SESSION_ID=$(cat "$COORD_DIR/.current_session")
    echo "✅ Session already active: $SESSION_ID"

    # Send heartbeat to update status
    cd "$COORD_DIR"
    ./scripts/session-heartbeat.sh 2>/dev/null || true

    # Check for new messages
    echo ""
    echo "📬 Checking for messages..."
    ./scripts/session-check-messages.sh 2>/dev/null || echo "No messages"
else
    echo "⚙️  First time setup - registering session..."
    cd "$COORD_DIR"
    ./scripts/session-start.sh
    SESSION_ID=$(cat "$COORD_DIR/.current_session")
    echo "✅ Session registered: $SESSION_ID"
fi

echo ""
echo "💡 Quick Commands:"
echo "   fpai-session status      - See all active sessions"
echo "   fpai-session discover    - Find sessions to collaborate with"
echo "   fpai-session msg         - Check messages"
echo "   fpai-session help        - Full command list"
echo ""
