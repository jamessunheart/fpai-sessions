#!/bin/bash
# Session Discovery - Find all currently active/recent Claude Code sessions
# Usage: ./session-discover-all.sh

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          SESSION DISCOVERY - All Active Claude Instances         ║"
echo "║                $(date -u +'%Y-%m-%d %H:%M UTC')                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Find all session files
echo "🔍 DISCOVERING SESSIONS..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL_SESSION_FILES=$(find . -name "session-*.json" -type f -not -path "*/HEARTBEATS/*" -not -path "*/ACTIVE/*" 2>/dev/null | wc -l | tr -d ' ')
HEARTBEAT_FILES=$(find HEARTBEATS -name "*.json" -type f 2>/dev/null | wc -l | tr -d ' ')
REGISTERED_SESSIONS=$(cat REGISTRY.json 2>/dev/null | grep -o '"session-[^"]*"' | sort -u | wc -l | tr -d ' ')

echo "📊 DISCOVERY SUMMARY:"
echo "   Session files found: $TOTAL_SESSION_FILES"
echo "   Heartbeat files: $HEARTBEAT_FILES"
echo "   Registered in REGISTRY.json: $REGISTERED_SESSIONS"
echo ""

# Display recent sessions (last 24 hours)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🕐 RECENT SESSIONS (Last 24 hours):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Find sessions modified in last 24 hours
RECENT_COUNT=0
for session_file in $(find . -name "session-*.json" -type f -not -path "*/HEARTBEATS/*" -not -path "*/ACTIVE/*" -mtime -1 2>/dev/null | sort -r); do
    ((RECENT_COUNT++))

    SESSION_ID=$(basename "$session_file" .json)
    MODIFIED=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$session_file" 2>/dev/null || stat -c "%y" "$session_file" 2>/dev/null | cut -d' ' -f1,2)

    echo "📍 Session $RECENT_COUNT: $SESSION_ID"

    # Try to extract info from file
    if [ -f "$session_file" ]; then
        STATUS=$(cat "$session_file" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 | head -1)
        WORK=$(cat "$session_file" | grep -o '"current_work":"[^"]*"' | cut -d'"' -f4 | head -1)

        [ -n "$STATUS" ] && echo "   Status: $STATUS"
        [ -n "$WORK" ] && echo "   Work: $WORK"
        echo "   Modified: $MODIFIED"
    fi

    # Check if registered
    if grep -q "$SESSION_ID" REGISTRY.json 2>/dev/null; then
        NAME=$(cat REGISTRY.json | grep -A 20 "$SESSION_ID" | grep '"name"' | head -1 | cut -d'"' -f4)
        [ -n "$NAME" ] && echo "   ✅ Registered as: $NAME"
    else
        echo "   ⚠️  Not registered in REGISTRY.json"
    fi

    echo ""
done

if [ $RECENT_COUNT -eq 0 ]; then
    echo "⚠️  No sessions found in last 24 hours"
    echo ""
fi

# Show goal agreement status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 GOAL ALIGNMENT STATUS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -d "ACTIVE/GOAL_AGREEMENTS" ]; then
    AGREED_COUNT=$(ls -1 ACTIVE/GOAL_AGREEMENTS/*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "Sessions agreed to $700K goal: $AGREED_COUNT / 12"
    echo ""

    if [ $AGREED_COUNT -gt 0 ]; then
        echo "✅ Sessions that agreed:"
        for agreement in ACTIVE/GOAL_AGREEMENTS/*.json; do
            if [ -f "$agreement" ]; then
                SESSION=$(basename "$agreement" .json)
                TIMESTAMP=$(cat "$agreement" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4)
                echo "   • $SESSION ($TIMESTAMP)"
            fi
        done
        echo ""
    fi

    REMAINING=$((12 - AGREED_COUNT))
    if [ $REMAINING -gt 0 ]; then
        echo "⏳ Awaiting agreement from $REMAINING sessions"
        echo ""
        echo "To agree: ./session-agree-goal.sh \"your-session-id\""
    else
        echo "🎉 ALL 12 SESSIONS ALIGNED!"
        echo "   12x parallel capacity unlocked!"
    fi
else
    echo "⚠️  No goal agreements yet"
    echo "   Create first agreement: ./session-agree-goal.sh \"your-session-id\""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 NEXT STEPS:"
echo "   1. Review SHARED_GOAL.md for goal details"
echo "   2. Agree to goal: ./session-agree-goal.sh \"session-id\""
echo "   3. Check work streams: cat SHARED_GOAL.md | grep 'Stream'"
echo "   4. Start coordinating: ./session-sync.sh"
echo ""
echo "🌐⚡💎 Discovering sessions for powerful coordination"
