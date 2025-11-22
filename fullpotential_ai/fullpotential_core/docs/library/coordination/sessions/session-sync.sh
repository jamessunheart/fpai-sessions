#!/bin/bash
# Session Sync - Show all active sessions and their current work
# Usage: ./session-sync.sh

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          MULTI-SESSION COORDINATION STATUS                       ║"
echo "║                $(date -u +'%Y-%m-%d %H:%M UTC')                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Count active sessions
TOTAL_SESSIONS=0
ACTIVE_SESSIONS=0
IDLE_SESSIONS=0

echo "📋 REGISTERED SESSIONS (from REGISTRY.json):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "REGISTRY.json" ]; then
    # Parse sessions from REGISTRY.json
    SESSION_IDS=$(cat REGISTRY.json | grep -o '"session-[^"]*"' | tr -d '"' | sort -u)

    for session_id in $SESSION_IDS; do
        ((TOTAL_SESSIONS++))

        # Get session details
        NAME=$(cat REGISTRY.json | grep -A 20 "$session_id" | grep '"name"' | head -1 | cut -d'"' -f4)
        ROLE=$(cat REGISTRY.json | grep -A 20 "$session_id" | grep '"role"' | head -1 | cut -d'"' -f4)
        STATUS=$(cat REGISTRY.json | grep -A 20 "$session_id" | grep '"status"' | head -1 | cut -d'"' -f4)
        WORK=$(cat REGISTRY.json | grep -A 20 "$session_id" | grep '"current_work"' | head -1 | cut -d'"' -f4)

        # Count status
        if [ "$STATUS" = "active" ]; then
            ((ACTIVE_SESSIONS++))
            STATUS_ICON="🟢"
        elif [ "$STATUS" = "completing" ]; then
            ((ACTIVE_SESSIONS++))
            STATUS_ICON="🔵"
        else
            ((IDLE_SESSIONS++))
            STATUS_ICON="⚪"
        fi

        echo ""
        echo "$STATUS_ICON $session_id"
        echo "   Name: $NAME"
        echo "   Role: $ROLE"
        echo "   Status: $STATUS"
        [ -n "$WORK" ] && echo "   Working on: $WORK"
    done
else
    echo "⚠️  REGISTRY.json not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "💓 RECENT HEARTBEATS (last 24 hours):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "HEARTBEATS" ]; then
    for heartbeat in HEARTBEATS/*.json; do
        if [ -f "$heartbeat" ]; then
            echo ""
            echo "💓 $(basename $heartbeat .json)"
            cat "$heartbeat" | grep -E "(name|role|status|current_work|last_heartbeat)" | sed 's/^/   /'
        fi
    done
else
    echo "⚠️  HEARTBEATS directory not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 SUMMARY:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Total Sessions: $TOTAL_SESSIONS"
echo "   Active: $ACTIVE_SESSIONS"
echo "   Idle: $IDLE_SESSIONS"
echo ""

echo "🔧 AVAILABLE TOOLS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ./session-find-help.sh \"capability\"       - Find who can help"
echo "   ./session-request-collaboration.sh         - Request help"
echo "   ./session-broadcast.sh \"message\"          - Send to all"
echo "   ./session-capability-match.sh              - Smart task matching"
echo ""

echo "🌐⚡💎 Multi-Session Coordination Active"
