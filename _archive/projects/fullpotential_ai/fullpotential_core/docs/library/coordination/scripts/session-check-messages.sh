#!/bin/bash

# 🤝 Session Check Messages - Check for new messages
# Shows broadcast messages and direct messages

set -e

cd "$(dirname "$0")/../.."

# Get current session ID
if [ ! -f "COORDINATION/.current_session" ]; then
    echo "⚠️  No active session"
    exit 1
fi

SESSION_ID=$(cat COORDINATION/.current_session)

echo "📬 Messages for $SESSION_ID"
echo ""

# Show broadcast messages (last 5)
echo "=== BROADCAST MESSAGES (last 5) ==="
if ls COORDINATION/messages/broadcast/*.json 1> /dev/null 2>&1; then
    ls -t COORDINATION/messages/broadcast/*.json 2>/dev/null | head -5 | while read msg; do
        if [ -f "$msg" ]; then
            FROM=$(python3 -c "import json; print(json.load(open('$msg')).get('from', 'unknown'))" 2>/dev/null || echo "unknown")
            SUBJECT=$(python3 -c "import json; print(json.load(open('$msg')).get('subject', ''))" 2>/dev/null || echo "")
            MESSAGE=$(python3 -c "import json; print(json.load(open('$msg')).get('message', ''))" 2>/dev/null || echo "")
            TIME=$(python3 -c "import json; print(json.load(open('$msg')).get('timestamp', ''))" 2>/dev/null || echo "")

            echo "From: $FROM"
            echo "Time: $TIME"
            echo "Subject: $SUBJECT"
            if [ -n "$MESSAGE" ]; then
                echo "Message: $MESSAGE"
            fi
            echo "---"
        fi
    done
else
    echo "(No broadcast messages)"
fi

echo ""

# Show direct messages (last 5)
echo "=== DIRECT MESSAGES (last 5) ==="
if [ -d "COORDINATION/messages/direct/${SESSION_ID}" ] && ls COORDINATION/messages/direct/${SESSION_ID}/*.json 1> /dev/null 2>&1; then
    ls -t COORDINATION/messages/direct/${SESSION_ID}/*.json 2>/dev/null | head -5 | while read msg; do
        if [ -f "$msg" ]; then
            FROM=$(python3 -c "import json; print(json.load(open('$msg')).get('from', 'unknown'))" 2>/dev/null || echo "unknown")
            SUBJECT=$(python3 -c "import json; print(json.load(open('$msg')).get('subject', ''))" 2>/dev/null || echo "")
            MESSAGE=$(python3 -c "import json; print(json.load(open('$msg')).get('message', ''))" 2>/dev/null || echo "")
            TIME=$(python3 -c "import json; print(json.load(open('$msg')).get('timestamp', ''))" 2>/dev/null || echo "")

            echo "From: $FROM"
            echo "Time: $TIME"
            echo "Subject: $SUBJECT"
            if [ -n "$MESSAGE" ]; then
                echo "Message: $MESSAGE"
            fi
            echo "---"
        fi
    done
else
    echo "(No direct messages)"
fi
