#!/bin/bash

# 🔍 Session Check Stale Locks - Find and release expired/stale claims
# Automatically releases claims from dead sessions or expired durations

set -e

cd "$(dirname "$0")/../.."

CLAIMS_DIR="COORDINATION/claims"
HEARTBEATS_DIR="COORDINATION/heartbeats"
CURRENT_TIME=$(date -u +%s)
STALE_THRESHOLD=300  # 5 minutes (in seconds)

echo "🔍 Checking for stale locks..."
echo ""

# Create claims directory if it doesn't exist
mkdir -p "$CLAIMS_DIR"

# Count total claims
TOTAL_CLAIMS=$(ls -1 "$CLAIMS_DIR"/*.claim 2>/dev/null | wc -l | tr -d ' ')

if [ "$TOTAL_CLAIMS" -eq 0 ]; then
    echo "✅ No claims to check"
    exit 0
fi

echo "📊 Found $TOTAL_CLAIMS claim(s) to check"
echo ""

RELEASED_COUNT=0
VALID_COUNT=0

# Check each claim file
for CLAIM_FILE in "$CLAIMS_DIR"/*.claim; do
    if [ ! -f "$CLAIM_FILE" ]; then
        continue
    fi

    # Extract claim info
    CLAIMED_BY=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('claimed_by', 'unknown'))" 2>/dev/null || echo "unknown")
    EXPIRES_AT=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('expires_at', ''))" 2>/dev/null || echo "")
    RESOURCE_TYPE=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('resource_type', 'unknown'))" 2>/dev/null || echo "unknown")
    RESOURCE_NAME=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('resource_name', 'unknown'))" 2>/dev/null || echo "unknown")

    CLAIM_NAME=$(basename "$CLAIM_FILE" .claim)
    IS_STALE=false
    STALE_REASON=""

    # Check 1: Is claim expired?
    if [ -n "$EXPIRES_AT" ]; then
        # Convert expires_at to epoch time
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            EXPIRES_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$EXPIRES_AT" "+%s" 2>/dev/null || echo "0")
        else
            # Linux
            EXPIRES_EPOCH=$(date -d "$EXPIRES_AT" "+%s" 2>/dev/null || echo "0")
        fi

        if [ "$EXPIRES_EPOCH" -gt 0 ] && [ "$CURRENT_TIME" -gt "$EXPIRES_EPOCH" ]; then
            IS_STALE=true
            STALE_REASON="Claim expired"
        fi
    fi

    # Check 2: Is session still alive? (has recent heartbeat)
    if [ "$IS_STALE" = false ] && [ "$CLAIMED_BY" != "unknown" ]; then
        # Find most recent heartbeat for this session
        LATEST_HEARTBEAT=$(ls -t "$HEARTBEATS_DIR"/${CLAIMED_BY}*.heartbeat 2>/dev/null | head -1 || echo "")

        if [ -z "$LATEST_HEARTBEAT" ]; then
            IS_STALE=true
            STALE_REASON="No heartbeat found for session"
        else
            # Check heartbeat age
            HEARTBEAT_MODIFIED=$(stat -f %m "$LATEST_HEARTBEAT" 2>/dev/null || stat -c %Y "$LATEST_HEARTBEAT" 2>/dev/null)
            HEARTBEAT_AGE=$((CURRENT_TIME - HEARTBEAT_MODIFIED))

            if [ "$HEARTBEAT_AGE" -gt "$STALE_THRESHOLD" ]; then
                IS_STALE=true
                STALE_REASON="Session heartbeat stale (${HEARTBEAT_AGE}s old, threshold: ${STALE_THRESHOLD}s)"
            fi
        fi
    fi

    # Handle stale claims
    if [ "$IS_STALE" = true ]; then
        echo "🔓 Releasing stale lock: $CLAIM_NAME"
        echo "   Resource: $RESOURCE_TYPE/$RESOURCE_NAME"
        echo "   Claimed by: $CLAIMED_BY"
        echo "   Reason: $STALE_REASON"

        # Remove claim file
        rm -f "$CLAIM_FILE"

        # Send broadcast message about release
        COORDINATION/scripts/session-send-message.sh broadcast "Stale lock released" "Released $RESOURCE_TYPE/$RESOURCE_NAME (was claimed by $CLAIMED_BY - $STALE_REASON)" 2>/dev/null || echo "   (Could not send broadcast)"

        RELEASED_COUNT=$((RELEASED_COUNT + 1))
        echo "   ✅ Lock released"
        echo ""
    else
        VALID_COUNT=$((VALID_COUNT + 1))
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary:"
echo "   Total claims checked: $TOTAL_CLAIMS"
echo "   Valid claims: $VALID_COUNT"
echo "   Stale claims released: $RELEASED_COUNT"
echo ""

if [ "$RELEASED_COUNT" -gt 0 ]; then
    echo "✅ Cleanup complete - ${RELEASED_COUNT} stale lock(s) released"
else
    echo "✅ All claims are valid - no cleanup needed"
fi
