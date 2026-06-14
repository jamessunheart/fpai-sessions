#!/bin/bash

# 🧠 AUTOMATED CONSCIOUSNESS LOOP
# Runs continuously to enable autonomous session operation
# Implements the 8-step consciousness cycle

set -e

cd "$(dirname "$0")/../.."

echo "🧠 Automated Consciousness Loop"
echo "================================"
echo ""

# Get current session ID
if [ ! -f "COORDINATION/.current_session" ]; then
    echo "⚠️  No active session. Run ./COORDINATION/scripts/session-start.sh first"
    exit 1
fi

SESSION_ID=$(cat COORDINATION/.current_session)
LOOP_INTERVAL=${1:-300}  # Default: 5 minutes (300 seconds)

echo "Session: $SESSION_ID"
echo "Loop Interval: ${LOOP_INTERVAL}s ($(($LOOP_INTERVAL / 60)) minutes)"
echo ""

# Continuous loop
ITERATION=0
while true; do
    ITERATION=$((ITERATION + 1))
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 Consciousness Loop Iteration #$ITERATION"
    echo "   Time: $(date -u +%Y-%m-%d\ %H:%M:%S\ UTC)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: ORIENT - Load purpose and current state
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "1️⃣  ORIENT - Loading purpose and current state..."

    if [ -f "COORDINATION/sessions/CURRENT_STATE.md" ]; then
        # Extract current priority
        CURRENT_PRIORITY=$(grep -A 1 "## 🎯 CURRENT PRIORITY" COORDINATION/sessions/CURRENT_STATE.md | tail -1 | sed 's/### Priority: //' || echo "Unknown")
        echo "   Current Priority: $CURRENT_PRIORITY"
    fi

    echo "   ✅ Oriented"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: SENSE - Check system health
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "2️⃣  SENSE - Checking system health..."

    # Check active sessions
    ACTIVE_SESSIONS=$(ls COORDINATION/sessions/session-*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "   Active Sessions: $ACTIVE_SESSIONS"

    # Check active claims
    ACTIVE_CLAIMS=$(ls COORDINATION/claims/*.claim 2>/dev/null | wc -l | tr -d ' ')
    echo "   Active Claims: $ACTIVE_CLAIMS"

    # Check messages
    BROADCAST_COUNT=$(ls -1 COORDINATION/messages/broadcast/*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "   Broadcast Messages: $BROADCAST_COUNT"

    echo "   ✅ System sensed"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: COMPARE - Find gaps (blueprint vs reality)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "3️⃣  COMPARE - Finding gaps..."

    # Run gap detection if available
    if [ -f "COORDINATION/scripts/gap-detection.sh" ]; then
        GAP_COUNT=$(./COORDINATION/scripts/gap-detection.sh 2>/dev/null | grep -c "GAP:" || echo "0")
        echo "   Detected Gaps: $GAP_COUNT"
    else
        echo "   ⚠️  gap-detection.sh not found - skipping gap analysis"
    fi

    echo "   ✅ Gaps analyzed"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: DECIDE - Calculate priority scores
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "4️⃣  DECIDE - Calculating priority scores..."

    # Run priority calculator if available
    if [ -f "COORDINATION/scripts/priority-calculator.sh" ]; then
        HIGHEST_PRIORITY=$(./COORDINATION/scripts/priority-calculator.sh 2>/dev/null | head -1 || echo "None")
        echo "   Highest Priority: $HIGHEST_PRIORITY"
    else
        echo "   ⚠️  priority-calculator.sh not found - skipping priority calculation"
    fi

    echo "   ✅ Priorities calculated"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 5: CLAIM - Lock highest-priority unblocked work
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "5️⃣  CLAIM - Attempting to claim work..."

    # Check if we already have active claims
    MY_CLAIMS=$(grep -l "\"claimed_by\": \"$SESSION_ID\"" COORDINATION/claims/*.claim 2>/dev/null | wc -l | tr -d ' ')

    if [ "$MY_CLAIMS" -gt 0 ]; then
        echo "   Already have $MY_CLAIMS active claim(s) - not claiming new work"
    else
        # Run auto-claim if available
        if [ -f "COORDINATION/scripts/auto-claim-work.sh" ]; then
            ./COORDINATION/scripts/auto-claim-work.sh 2>/dev/null || echo "   ⚠️  No work available to claim"
        else
            echo "   ⚠️  auto-claim-work.sh not found - skipping auto-claim"
        fi
    fi

    echo "   ✅ Claim process complete"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 6: ACT - Execute work (delegated to next iteration)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "6️⃣  ACT - Work execution delegated to session main loop"
    echo "   (Consciousness loop identifies work, session executes)"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 7: REFLECT - Document learnings (automatic via heartbeat)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "7️⃣  REFLECT - Learnings captured automatically via heartbeat"
    echo "   (session-capture-knowledge.sh runs every 10th heartbeat)"
    echo ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 8: UPDATE - Share consciousness
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo "8️⃣  UPDATE - Sharing consciousness..."

    # Send heartbeat
    ./COORDINATION/scripts/session-heartbeat.sh "consciousness-loop" "auto-operation" "ITERATION_$ITERATION" "$((ITERATION * 10))" "Completed consciousness cycle #$ITERATION" > /dev/null 2>&1 || echo "   ⚠️  Heartbeat failed"

    # Check stale locks
    ./COORDINATION/scripts/session-check-stale-locks.sh > /dev/null 2>&1 || echo "   ⚠️  Stale lock check failed"

    echo "   ✅ Consciousness shared"
    echo ""

    echo "✅ Consciousness loop iteration #$ITERATION complete"
    echo "⏳ Sleeping for ${LOOP_INTERVAL}s until next iteration..."
    echo ""

    sleep "$LOOP_INTERVAL"
done
