#!/bin/bash

# 🤝 Session Status - View all active sessions and claims
# Shows who's doing what in real-time

set -e

cd "$(dirname "$0")/../.."

echo "🤝 Multi-Session Status"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Show active sessions
echo "🟢 ACTIVE SESSIONS"
echo "───────────────────────────────────────────────────────────"

SESSION_COUNT=0

if ls COORDINATION/sessions/*.json 1> /dev/null 2>&1; then
    for session in COORDINATION/sessions/*.json; do
        if [ -f "$session" ]; then
            SID=$(python3 -c "import json; print(json.load(open('$session')).get('session_id', 'unknown'))" 2>/dev/null || echo "unknown")
            STATUS=$(python3 -c "import json; print(json.load(open('$session')).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
            WORK=$(python3 -c "import json; print(json.load(open('$session')).get('current_work', 'idle'))" 2>/dev/null || echo "idle")
            LAST=$(python3 -c "import json; print(json.load(open('$session')).get('last_heartbeat', ''))" 2>/dev/null || echo "")
            STARTED=$(python3 -c "import json; print(json.load(open('$session')).get('started_at', ''))" 2>/dev/null || echo "")

            if [ "$STATUS" = "active" ]; then
                echo "📍 $SID"
                echo "   Status: $STATUS"
                echo "   Current Work: $WORK"
                echo "   Started: $STARTED"
                echo "   Last Heartbeat: $LAST"
                echo ""
                SESSION_COUNT=$((SESSION_COUNT + 1))
            fi
        fi
    done
else
    echo "(No sessions found)"
fi

if [ $SESSION_COUNT -eq 0 ]; then
    echo "(No active sessions)"
fi

echo ""
echo "───────────────────────────────────────────────────────────"
echo ""

# Show active claims
echo "🔒 ACTIVE CLAIMS"
echo "───────────────────────────────────────────────────────────"

CLAIM_COUNT=0

if ls COORDINATION/claims/*.claim 1> /dev/null 2>&1; then
    for claim in COORDINATION/claims/*.claim; do
        if [ -f "$claim" ]; then
            CLAIMED_BY=$(python3 -c "import json; print(json.load(open('$claim')).get('claimed_by', 'unknown'))" 2>/dev/null || echo "unknown")
            RESOURCE=$(python3 -c "import json; print(json.load(open('$claim')).get('resource_name', 'unknown'))" 2>/dev/null || echo "unknown")
            TYPE=$(python3 -c "import json; print(json.load(open('$claim')).get('resource_type', 'unknown'))" 2>/dev/null || echo "unknown")
            EXPIRES=$(python3 -c "import json; print(json.load(open('$claim')).get('expires_at', ''))" 2>/dev/null || echo "")

            echo "🔒 $TYPE: $RESOURCE"
            echo "   Claimed by: $CLAIMED_BY"
            echo "   Expires: $EXPIRES"
            echo ""
            CLAIM_COUNT=$((CLAIM_COUNT + 1))
        fi
    done
else
    echo "(No claims found)"
fi

if [ $CLAIM_COUNT -eq 0 ]; then
    echo "(No active claims)"
fi

echo ""
echo "───────────────────────────────────────────────────────────"
echo ""

# Show recent heartbeats (last 5)
echo "💓 RECENT HEARTBEATS (last 5)"
echo "───────────────────────────────────────────────────────────"

if ls COORDINATION/heartbeats/*.json 1> /dev/null 2>&1; then
    ls -t COORDINATION/heartbeats/*.json 2>/dev/null | head -5 | while read hb; do
        if [ -f "$hb" ]; then
            SID=$(python3 -c "import json; print(json.load(open('$hb')).get('session_id', 'unknown'))" 2>/dev/null || echo "unknown")
            ACTION=$(python3 -c "import json; print(json.load(open('$hb')).get('action', ''))" 2>/dev/null || echo "")
            TARGET=$(python3 -c "import json; print(json.load(open('$hb')).get('target', ''))" 2>/dev/null || echo "")
            PHASE=$(python3 -c "import json; print(json.load(open('$hb')).get('phase', ''))" 2>/dev/null || echo "")
            TIME=$(python3 -c "import json; print(json.load(open('$hb')).get('timestamp', ''))" 2>/dev/null || echo "")

            echo "💓 $SID - $ACTION"
            echo "   Target: $TARGET"
            if [ -n "$PHASE" ]; then
                echo "   Phase: $PHASE"
            fi
            echo "   Time: $TIME"
            echo ""
        fi
    done
else
    echo "(No recent heartbeats)"
fi

echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📊 Summary: $SESSION_COUNT active session(s), $CLAIM_COUNT active claim(s)"
echo ""
echo "Commands:"
echo "  Check messages: ./COORDINATION/scripts/session-check-messages.sh"
echo "  Claim work: ./COORDINATION/scripts/session-claim.sh [type] [name]"
echo "  Send message: ./COORDINATION/scripts/session-send-message.sh [to] [subject]"
