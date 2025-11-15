#!/bin/bash
# Quick status check for all sessions and priorities

SESSIONS_DIR="$HOME/Development/SESSIONS"
cd "$SESSIONS_DIR" || exit 1

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 MULTI-SESSION STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Show active sessions from heartbeats
echo "📡 ACTIVE SESSIONS (Last 5 minutes):"
echo ""
if [ -d "HEARTBEATS" ] && [ "$(ls -A HEARTBEATS/*.json 2>/dev/null)" ]; then
    for heartbeat in HEARTBEATS/*.json; do
        if [ -f "$heartbeat" ]; then
            SESSION_ID=$(jq -r '.session_id' "$heartbeat" 2>/dev/null || echo "unknown")
            TIMESTAMP=$(jq -r '.timestamp' "$heartbeat" 2>/dev/null || echo "unknown")
            STATUS=$(jq -r '.status' "$heartbeat" 2>/dev/null || echo "unknown")
            echo "  ✅ $SESSION_ID"
            echo "     Last seen: $TIMESTAMP"
            echo "     Status: $STATUS"
            echo ""
        fi
    done
else
    echo "  ⚠️  No active heartbeats found"
    echo ""
fi

# Show registered sessions
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 REGISTERED SESSIONS:"
echo ""
if [ -f "REGISTRY.json" ]; then
    jq -r '.sessions | to_entries[] | "  \(.value.id)\n    Role: \(.value.role)\n    Status: \(.value.status)\n    Agreed: \(.value.agreed)\n"' REGISTRY.json
else
    echo "  ⚠️  REGISTRY.json not found"
fi

# Show claimed priorities
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔒 CLAIMED PRIORITIES:"
echo ""
if [ -d "PRIORITIES" ] && [ "$(ls -A PRIORITIES/*.lock 2>/dev/null)" ]; then
    for lock in PRIORITIES/*.lock; do
        if [ -f "$lock" ]; then
            PRIORITY_ID=$(jq -r '.priority_id' "$lock" 2>/dev/null || echo "unknown")
            SESSION_ID=$(jq -r '.session_id' "$lock" 2>/dev/null || echo "unknown")
            CLAIMED_AT=$(jq -r '.claimed_at' "$lock" 2>/dev/null || echo "unknown")
            echo "  🔒 $PRIORITY_ID"
            echo "     Claimed by: $SESSION_ID"
            echo "     At: $CLAIMED_AT"
            echo ""
        fi
    done
else
    echo "  ✅ No priorities currently claimed"
    echo ""
fi

# Show active milestones
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 ACTIVE MILESTONES:"
echo ""
if [ -d "MILESTONES" ] && [ "$(ls -A MILESTONES/*.json 2>/dev/null)" ]; then
    for milestone_file in MILESTONES/*.json; do
        if [ -f "$milestone_file" ]; then
            title=$(jq -r '.title' "$milestone_file" 2>/dev/null)
            status=$(jq -r '.status' "$milestone_file" 2>/dev/null)
            progress=$(jq -r '.progress' "$milestone_file" 2>/dev/null)
            owner=$(jq -r '.owner' "$milestone_file" 2>/dev/null)
            priority=$(jq -r '.priority' "$milestone_file" 2>/dev/null)

            # Only show non-completed milestones
            if [ "$status" != "completed" ]; then
                case "$status" in
                    pending) icon="⏳" ;;
                    in_progress) icon="🔄" ;;
                    blocked) icon="🚫" ;;
                    *) icon="❓" ;;
                esac

                case "$priority" in
                    HIGH) priority_icon="🔴" ;;
                    MEDIUM) priority_icon="🟡" ;;
                    LOW) priority_icon="🟢" ;;
                    *) priority_icon="⚪" ;;
                esac

                echo "  $icon $priority_icon $title"
                echo "     Progress: $progress% | Owner: $owner | Status: $status"
                echo ""
            fi
        fi
    done
else
    echo "  ✅ No active milestones"
    echo ""
fi

# Show current priority from CURRENT_STATE.md
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 CURRENT PRIORITY (from CURRENT_STATE.md):"
echo ""
if [ -f "CURRENT_STATE.md" ]; then
    # Extract current priority section (lines between "## 🎯 CURRENT PRIORITY" and next "##")
    sed -n '/## 🎯 CURRENT PRIORITY/,/^## /p' CURRENT_STATE.md | sed '$d' | tail -n +3
else
    echo "  ⚠️  CURRENT_STATE.md not found"
fi

# Show recent messages
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📬 RECENT MESSAGES (Last 10 lines):"
echo ""
if [ -f "MESSAGES.md" ]; then
    tail -n 10 MESSAGES.md
else
    echo "  ⚠️  MESSAGES.md not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Status check complete"
echo ""
echo "Commands:"
echo "  cat SESSIONS/CURRENT_STATE.md           - Full state"
echo "  cat SESSIONS/MESSAGES.md                - All messages"
echo "  cat SESSIONS/REGISTRY.json              - Session directory"
echo "  ./SESSIONS/milestone-status.sh          - Detailed milestone view"
echo "  ./SESSIONS/claim-milestone.sh <id> <s>  - Claim a milestone"
echo ""
