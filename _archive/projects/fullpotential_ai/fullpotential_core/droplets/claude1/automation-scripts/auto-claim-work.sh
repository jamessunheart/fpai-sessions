#!/bin/bash

# 🤖 AUTO-CLAIM WORK - Autonomously claim highest-priority unclaimed work
# Enables true autonomous operation

set -e

cd "$(dirname "$0")/../.."

# Get current session ID
if [ ! -f "COORDINATION/.current_session" ]; then
    echo "⚠️  No active session"
    exit 1
fi

SESSION_ID=$(cat COORDINATION/.current_session)

echo "🤖 Auto-Claim Work - Autonomous Mode"
echo "====================================="
echo "Session: $SESSION_ID"
echo ""

# Define available work items
# Format: "type:name:duration_hours:min_unblocked_score"
declare -a AVAILABLE_WORK=(
    "script:unified-work-registry:4:10"
    "script:monitoring-dashboard:2:10"
    "service:orchestrator-restart:1:8"
    "doc:service-specs:3:10"
)

echo "📋 Checking available work..."
echo ""

CLAIMED=false

for item in "${AVAILABLE_WORK[@]}"; do
    IFS=':' read -r type name duration min_score <<< "$item"

    # Check if already claimed
    CLAIM_FILE="COORDINATION/claims/${type}-${name}.claim"

    if [ -f "$CLAIM_FILE" ]; then
        CLAIMED_BY=$(python3 -c "import json; print(json.load(open('$CLAIM_FILE')).get('claimed_by', 'unknown'))" 2>/dev/null || echo "unknown")
        echo "⏭️  $type/$name - Already claimed by $CLAIMED_BY"
        continue
    fi

    # Check if work meets minimum unblocked score
    # (In real implementation, this would query priority-calculator.sh)
    # For now, we'll claim if unclaimed and no other active claims exist

    MY_CLAIMS=$(grep -l "\"claimed_by\": \"$SESSION_ID\"" COORDINATION/claims/*.claim 2>/dev/null | wc -l | tr -d ' ')

    if [ "$MY_CLAIMS" -gt 0 ]; then
        echo "⏭️  $type/$name - Skipping (already have $MY_CLAIMS active claim)"
        continue
    fi

    # Claim this work!
    echo "🎯 Claiming: $type/$name (duration: ${duration}h)"

    ./COORDINATION/scripts/session-claim.sh "$type" "$name" "$duration" > /dev/null 2>&1 || {
        echo "   ⚠️  Claim failed"
        continue
    }

    echo "   ✅ Successfully claimed!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Work Claimed: $type/$name"
    echo "Duration: ${duration} hours"
    echo "Claimed By: $SESSION_ID"
    echo "Next: Execute this work in your main session"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    CLAIMED=true
    break
done

if [ "$CLAIMED" = false ]; then
    echo "ℹ️  No unclaimed work available"
    echo "   Either all work is claimed or session has active claims"
fi
