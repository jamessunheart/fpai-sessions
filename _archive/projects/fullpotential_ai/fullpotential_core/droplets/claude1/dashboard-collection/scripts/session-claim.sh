#!/bin/bash

# 🤝 Session Claim - Claim work to prevent conflicts
# Usage: ./session-claim.sh [resource_type] [resource_name] [duration_hours]

set -e

cd "$(dirname "$0")/../.."

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./session-claim.sh [resource_type] [resource_name] [duration_hours]"
    echo ""
    echo "Examples:"
    echo "  ./session-claim.sh droplet church-guidance-ministry 4"
    echo "  ./session-claim.sh file CONSCIOUSNESS.md 1"
    echo "  ./session-claim.sh deployment production 2"
    exit 1
fi

RESOURCE_TYPE=$1
RESOURCE_NAME=$2
DURATION_HOURS=${3:-4}  # Default 4 hours

# Get current session ID
if [ ! -f "COORDINATION/.current_session" ]; then
    echo "⚠️  No active session. Run ./COORDINATION/scripts/session-start.sh first"
    exit 1
fi

SESSION_ID=$(cat COORDINATION/.current_session)
CLAIM_FILE="COORDINATION/claims/${RESOURCE_TYPE}-${RESOURCE_NAME}.claim"

# Check if already claimed
if [ -f "$CLAIM_FILE" ]; then
    CLAIMED_BY=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('claimed_by', 'unknown'))")
    EXPIRES_AT=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('expires_at', ''))")

    if [ "$CLAIMED_BY" = "$SESSION_ID" ]; then
        echo "✅ Already claimed by you ($SESSION_ID)"
        echo "   Claim file: $CLAIM_FILE"
        exit 0
    else
        echo "⚠️  Already claimed by: $CLAIMED_BY"
        echo "   Expires: $EXPIRES_AT"
        echo "   Claim file: $CLAIM_FILE"
        echo ""
        echo "Options:"
        echo "  1. Wait for claim to expire"
        echo "  2. Coordinate with $CLAIMED_BY (send message)"
        echo "  3. Pick different work"
        exit 1
    fi
fi

# Calculate expiration (duration from now)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    EXPIRES_AT=$(date -u -v +${DURATION_HOURS}H +%Y-%m-%dT%H:%M:%SZ)
else
    # Linux
    EXPIRES_AT=$(date -u -d "+${DURATION_HOURS} hours" +%Y-%m-%dT%H:%M:%SZ)
fi

# Create claim
cat > "$CLAIM_FILE" <<EOF
{
  "claimed_by": "$SESSION_ID",
  "claimed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "resource_type": "$RESOURCE_TYPE",
  "resource_name": "$RESOURCE_NAME",
  "duration_hours": $DURATION_HOURS,
  "expires_at": "$EXPIRES_AT",
  "allow_coordination": true
}
EOF

# Send heartbeat
COORDINATION/scripts/session-heartbeat.sh "claimed" "$RESOURCE_TYPE/$RESOURCE_NAME" "CLAIMED"

# Send broadcast
COORDINATION/scripts/session-send-message.sh broadcast "Work claimed" "$SESSION_ID claimed $RESOURCE_TYPE: $RESOURCE_NAME"

echo "✅ Claimed: $RESOURCE_TYPE/$RESOURCE_NAME"
echo "   By: $SESSION_ID"
echo "   Expires: $EXPIRES_AT"
echo "   Claim file: $CLAIM_FILE"
