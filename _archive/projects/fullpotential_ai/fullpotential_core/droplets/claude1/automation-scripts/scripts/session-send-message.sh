#!/bin/bash

# 🤝 Session Send Message - Send messages to other sessions
# Usage: ./session-send-message.sh [to] [subject] [message]

set -e

cd "$(dirname "$0")/../.."

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./session-send-message.sh [to] [subject] [message]"
    echo ""
    echo "Examples:"
    echo "  ./session-send-message.sh broadcast 'Work complete' 'Dashboard deployed'"
    echo "  ./session-send-message.sh session-123 'Question' 'Can you help with X?'"
    exit 1
fi

TO=$1
SUBJECT=$2
MESSAGE=${3:-""}

# Get current session ID
if [ ! -f "COORDINATION/.current_session" ]; then
    echo "⚠️  No active session"
    exit 1
fi

SESSION_ID=$(cat COORDINATION/.current_session)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

# Determine message file location
if [ "$TO" = "broadcast" ]; then
    MSG_FILE="COORDINATION/messages/broadcast/${TIMESTAMP}-${SESSION_ID}.json"
else
    mkdir -p "COORDINATION/messages/direct/${TO}"
    MSG_FILE="COORDINATION/messages/direct/${TO}/${TIMESTAMP}-${SESSION_ID}.json"
fi

# Create message file
cat > "$MSG_FILE" <<EOF
{
  "from": "$SESSION_ID",
  "to": "$TO",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "subject": "$SUBJECT",
  "message": "$MESSAGE"
}
EOF

echo "✅ Message sent to $TO"
