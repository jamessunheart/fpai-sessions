#!/bin/bash
# Show status of all milestones

MILESTONES_DIR="$HOME/Development/SESSIONS/MILESTONES"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 MILESTONE STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -d "$MILESTONES_DIR" ]; then
    echo "⚠️  MILESTONES directory not found"
    exit 1
fi

# Count milestones by status
total=0
pending=0
in_progress=0
completed=0
blocked=0

for milestone_file in "$MILESTONES_DIR"/*.json; do
    [ -f "$milestone_file" ] || continue

    total=$((total + 1))

    # Extract key info
    milestone_id=$(jq -r '.milestone_id' "$milestone_file" 2>/dev/null)
    title=$(jq -r '.title' "$milestone_file" 2>/dev/null)
    status=$(jq -r '.status' "$milestone_file" 2>/dev/null)
    progress=$(jq -r '.progress' "$milestone_file" 2>/dev/null)
    owner=$(jq -r '.owner' "$milestone_file" 2>/dev/null)
    priority=$(jq -r '.priority' "$milestone_file" 2>/dev/null)
    updated=$(jq -r '.updated_at' "$milestone_file" 2>/dev/null)

    # Count by status
    case "$status" in
        pending) pending=$((pending + 1)) ;;
        in_progress) in_progress=$((in_progress + 1)) ;;
        completed) completed=$((completed + 1)) ;;
        blocked) blocked=$((blocked + 1)) ;;
    esac

    # Status icon
    case "$status" in
        pending) icon="⏳" ;;
        in_progress) icon="🔄" ;;
        completed) icon="✅" ;;
        blocked) icon="🚫" ;;
        *) icon="❓" ;;
    esac

    # Priority icon
    case "$priority" in
        HIGH) priority_icon="🔴" ;;
        MEDIUM) priority_icon="🟡" ;;
        LOW) priority_icon="🟢" ;;
        *) priority_icon="⚪" ;;
    esac

    echo "$icon $priority_icon $title"
    echo "   ID: $milestone_id"
    echo "   Status: $status ($progress% complete)"
    echo "   Owner: $owner"
    echo "   Updated: $updated"

    # Show next steps if in progress
    if [ "$status" = "in_progress" ]; then
        next_steps=$(jq -r '.next_session_should[]' "$milestone_file" 2>/dev/null | head -1)
        if [ -n "$next_steps" ]; then
            echo "   Next: $next_steps"
        fi
    fi

    # Show blockers if blocked
    if [ "$status" = "blocked" ]; then
        blockers=$(jq -r '.blockers[]' "$milestone_file" 2>/dev/null | head -1)
        if [ -n "$blockers" ]; then
            echo "   Blocker: $blockers"
        fi
    fi

    echo ""
done

if [ $total -eq 0 ]; then
    echo "No milestones found"
    echo ""
    echo "Create one with: ./SESSIONS/create-milestone.sh"
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Total: $total"
    echo "⏳ Pending: $pending"
    echo "🔄 In Progress: $in_progress"
    echo "✅ Completed: $completed"
    echo "🚫 Blocked: $blocked"
fi

echo ""
echo "Commands:"
echo "  ./SESSIONS/claim-milestone.sh <id> <session>  - Claim a milestone"
echo "  ./SESSIONS/update-milestone.sh <id> <step> <status> - Update progress"
echo "  cat SESSIONS/MILESTONES/<id>.json             - View full details"
echo ""
