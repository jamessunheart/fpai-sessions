#!/bin/bash

# 🤝 Session Release - Release claimed work
# Usage: ./session-release.sh [resource_type] [resource_name]

set -e

cd "$(dirname "$0")/../.."

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./session-release.sh [resource_type] [resource_name]"
    echo ""
    echo "Examples:"
    echo "  ./session-release.sh droplet church-guidance-ministry"
    echo "  ./session-release.sh file CONSCIOUSNESS.md"
    exit 1
fi

RESOURCE_TYPE=$1
RESOURCE_NAME=$2

# Get current session ID
if [ ! -f "COORDINATION/.current_session" ]; then
    echo "⚠️  No active session"
    exit 1
fi

SESSION_ID=$(cat COORDINATION/.current_session)
CLAIM_FILE="COORDINATION/claims/${RESOURCE_TYPE}-${RESOURCE_NAME}.claim"

# Check if claim exists
if [ ! -f "$CLAIM_FILE" ]; then
    echo "⚠️  No claim found for $RESOURCE_TYPE/$RESOURCE_NAME"
    exit 1
fi

# Verify it's our claim
CLAIMED_BY=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('claimed_by', 'unknown'))")

if [ "$CLAIMED_BY" != "$SESSION_ID" ]; then
    echo "⚠️  Claim belongs to $CLAIMED_BY, not $SESSION_ID"
    exit 1
fi

# Release claim
rm "$CLAIM_FILE"

# Send heartbeat
COORDINATION/scripts/session-heartbeat.sh "released" "$RESOURCE_TYPE/$RESOURCE_NAME" "RELEASED"

# Send broadcast
COORDINATION/scripts/session-send-message.sh broadcast "Work released" "$SESSION_ID released $RESOURCE_TYPE: $RESOURCE_NAME - available for others"

echo "✅ Released: $RESOURCE_TYPE/$RESOURCE_NAME"
