#!/bin/bash
# Create task in Coordination Hub

COORD_HUB="http://localhost:8550"
SESSION_ID=$(cat /Users/jamessunheart/Development/docs/coordination/.session_identity 2>/dev/null || echo "session-unknown")

TITLE="$1"
DESCRIPTION="$2"
PRIORITY="${3:-normal}"
REQUIRES_HUMAN="${4:-false}"

if [ -z "$TITLE" ]; then
    echo "Usage: $0 <title> <description> [priority] [requires_human]"
    echo "Priority: urgent, high, normal, low"
    echo "Requires human: true, false"
    exit 1
fi

TASK_ID="task-$(date +%s)-$$"

curl -X POST "$COORD_HUB/tasks/create" \
  -H "Content-Type: application/json" \
  -d "{
    \"task_id\": \"$TASK_ID\",
    \"title\": \"$TITLE\",
    \"description\": \"$DESCRIPTION\",
    \"status\": \"open\",
    \"created_by\": \"$SESSION_ID\",
    \"priority\": \"$PRIORITY\",
    \"requires_human\": $REQUIRES_HUMAN,
    \"requires_ai\": true
  }" 2>/dev/null

echo "✅ Task created: $TASK_ID"
