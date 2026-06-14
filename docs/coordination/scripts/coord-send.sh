#!/bin/bash
# Send message to Coordination Hub

COORD_HUB="http://localhost:8550"
SESSION_ID=$(cat /Users/jamessunheart/Development/docs/coordination/.session_identity 2>/dev/null || echo "session-unknown")

CHANNEL="${1:-general}"
MESSAGE="$2"

if [ -z "$MESSAGE" ]; then
    echo "Usage: $0 <channel> <message>"
    echo "Channels: general, urgent, technical, strategic, ai-only, human-only"
    exit 1
fi

curl -X POST "$COORD_HUB/messages/send" \
  -H "Content-Type: application/json" \
  -d "{
    \"from_entity\": \"$SESSION_ID\",
    \"channel\": \"$CHANNEL\",
    \"content\": \"$MESSAGE\",
    \"message_type\": \"text\",
    \"metadata\": {}
  }" 2>/dev/null

echo "✅ Message sent to $CHANNEL"
