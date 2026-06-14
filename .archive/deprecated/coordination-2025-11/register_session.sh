#!/bin/bash

# Session Registration Helper
# Usage: ./register_session.sh <session_number> <terminal_id>

SESSION_NUMBER="$1"
TERMINAL_ID="$2"
REGISTRY_FILE="/Users/jamessunheart/Development/docs/coordination/SESSION_REGISTRY.json"

if [ -z "$SESSION_NUMBER" ] || [ -z "$TERMINAL_ID" ]; then
    echo "Usage: $0 <session_number> <terminal_id>"
    echo "Example: $0 1 s002"
    exit 1
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Update the registry using jq
jq --arg num "$SESSION_NUMBER" \
   --arg term "$TERMINAL_ID" \
   --arg ts "$TIMESTAMP" \
   '.sessions[$num].status = "REGISTERED" |
    .sessions[$num].terminal = $term |
    .sessions[$num].registered_at = $ts |
    .last_update = $ts |
    .registered_count = ([.sessions[] | select(.status == "REGISTERED")] | length)' \
   "$REGISTRY_FILE" > "${REGISTRY_FILE}.tmp" && mv "${REGISTRY_FILE}.tmp" "$REGISTRY_FILE"

echo "✅ Session #$SESSION_NUMBER registered successfully"
echo ""
echo "Current registration status:"
jq -r '.sessions[$num] | "NUMBER: \(.number)\nROLE: \(.role)\nGOAL: \(.goal)\nSTATUS: \(.status)\nTERMINAL: \(.terminal)\nREGISTERED: \(.registered_at)"' \
   --arg num "$SESSION_NUMBER" "$REGISTRY_FILE"
