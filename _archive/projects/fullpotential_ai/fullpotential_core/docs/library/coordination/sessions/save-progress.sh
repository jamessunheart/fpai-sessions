#!/bin/bash
# Save progress across the coordination system
# Can be called with different modes: quick, milestone, full

MODE="${1:-auto}"
SESSION_ID="${2:-session-unknown}"
SESSIONS_DIR="$HOME/Development/SESSIONS"

cd "$SESSIONS_DIR" || exit 1

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 SAVING PROGRESS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Mode: $MODE"
echo "Session: $SESSION_ID"
echo ""

# Function to update heartbeat
update_heartbeat() {
    local session="$1"
    local work="$2"

    cat > "HEARTBEATS/${session}.json" << EOF
{
  "session_id": "$session",
  "timestamp": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
  "status": "active",
  "current_work": "$work",
  "last_save": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")"
}
EOF
    echo "  ✅ Heartbeat updated"
}

# Function to detect active milestone
detect_milestone() {
    local session="$1"

    # Check if session has claimed a milestone
    for lock in PRIORITIES/milestone-*.lock; do
        [ -f "$lock" ] || continue

        claimed_by=$(jq -r '.session_id' "$lock" 2>/dev/null)
        if [ "$claimed_by" = "$session" ]; then
            milestone_id=$(jq -r '.milestone_id' "$lock" 2>/dev/null)
            echo "$milestone_id"
            return 0
        fi
    done

    # Check for in-progress milestones owned by this session
    for milestone in MILESTONES/*.json; do
        [ -f "$milestone" ] || continue

        owner=$(jq -r '.owner' "$milestone" 2>/dev/null)
        status=$(jq -r '.status' "$milestone" 2>/dev/null)

        if [ "$owner" = "$session" ] && [ "$status" = "in_progress" ]; then
            jq -r '.milestone_id' "$milestone" 2>/dev/null
            return 0
        fi
    done

    return 1
}

# AUTO MODE: Detect what to save based on context
if [ "$MODE" = "auto" ]; then
    echo "🔍 Auto-detecting save context..."
    echo ""

    # Check if session has active milestone
    if active_milestone=$(detect_milestone "$SESSION_ID"); then
        echo "  📍 Found active milestone: $active_milestone"
        MODE="milestone"
    else
        echo "  📍 No active milestone detected"
        MODE="quick"
    fi
    echo ""
fi

# QUICK SAVE: Just update heartbeat
if [ "$MODE" = "quick" ]; then
    echo "💨 QUICK SAVE (heartbeat only)"
    echo ""

    # Prompt for current work
    if [ -t 0 ]; then
        echo "What are you working on?"
        read -r current_work
    else
        current_work="In progress"
    fi

    update_heartbeat "$SESSION_ID" "$current_work"

    echo ""
    echo "✅ Quick save complete"
fi

# MILESTONE SAVE: Update milestone progress
if [ "$MODE" = "milestone" ]; then
    echo "🎯 MILESTONE SAVE"
    echo ""

    # Detect or prompt for milestone
    if [ -z "$active_milestone" ]; then
        active_milestone=$(detect_milestone "$SESSION_ID")
    fi

    if [ -z "$active_milestone" ]; then
        echo "❌ No active milestone found for $SESSION_ID"
        echo ""
        echo "Available milestones:"
        ls -1 MILESTONES/*.json 2>/dev/null | xargs -n1 basename | sed 's/.json$//'
        exit 1
    fi

    milestone_file="MILESTONES/${active_milestone}.json"

    echo "  Milestone: $active_milestone"
    echo ""

    # Show current progress
    title=$(jq -r '.title' "$milestone_file")
    progress=$(jq -r '.progress' "$milestone_file")

    echo "  📊 Current: $title ($progress%)"
    echo ""

    # Show pending steps
    echo "  Pending steps:"
    jq -r '.steps[] | select(.status == "pending" or .status == "in_progress") | "    [\(.step)] \(.description)"' "$milestone_file"
    echo ""

    # Prompt for step to mark complete
    if [ -t 0 ]; then
        echo "Which step did you complete? (number or 'none')"
        read -r step_num

        if [ "$step_num" != "none" ] && [ -n "$step_num" ]; then
            echo "Brief note about completion:"
            read -r completion_note

            # Update milestone
            ../SESSIONS/update-milestone.sh "$active_milestone" "$step_num" "completed" "$completion_note" "$SESSION_ID"
            echo ""
        fi
    fi

    update_heartbeat "$SESSION_ID" "Working on: $title"

    echo ""
    echo "✅ Milestone save complete"
fi

# FULL SAVE: Update everything + commit to git
if [ "$MODE" = "full" ]; then
    echo "🔄 FULL SAVE (milestone + CURRENT_STATE + git)"
    echo ""

    # First do milestone save if applicable
    if active_milestone=$(detect_milestone "$SESSION_ID"); then
        echo "1️⃣ Updating milestone: $active_milestone"
        bash "$0" milestone "$SESSION_ID"
        echo ""
    fi

    # Update CURRENT_STATE.md
    echo "2️⃣ Updating CURRENT_STATE.md"
    echo ""

    # Update the "Last Updated" timestamp
    timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    temp_file=$(mktemp)

    # Update timestamp and session info at top of CURRENT_STATE.md
    awk -v ts="$timestamp" -v session="$SESSION_ID" '
        /^\*\*Last Updated:/ { print "**Last Updated:** " ts; next }
        /^\*\*Updated By:/ { print "**Updated By:** " session; next }
        { print }
    ' CURRENT_STATE.md > "$temp_file"
    mv "$temp_file" CURRENT_STATE.md

    echo "  ✅ CURRENT_STATE.md timestamp updated"
    echo ""

    # Commit to git if in git repo
    echo "3️⃣ Committing to git"
    echo ""

    cd "$HOME/Development" || exit 1

    if git rev-parse --git-dir > /dev/null 2>&1; then
        # Add SESSIONS files
        git add SESSIONS/

        # Create commit message
        if [ -n "$active_milestone" ]; then
            milestone_title=$(jq -r '.title' "SESSIONS/MILESTONES/${active_milestone}.json")
            milestone_progress=$(jq -r '.progress' "SESSIONS/MILESTONES/${active_milestone}.json")
            commit_msg="Save progress: $milestone_title ($milestone_progress% complete)

Session: $SESSION_ID
Timestamp: $timestamp

🤖 Auto-saved via save-progress.sh"
        else
            commit_msg="Save session progress

Session: $SESSION_ID
Timestamp: $timestamp

🤖 Auto-saved via save-progress.sh"
        fi

        # Commit
        if git diff --cached --quiet; then
            echo "  ℹ️  No changes to commit"
        else
            git commit -m "$commit_msg"
            echo "  ✅ Changes committed to git"

            # Optionally push (if user wants auto-push)
            if [ "$AUTO_PUSH" = "true" ]; then
                git push
                echo "  ✅ Changes pushed to remote"
            fi
        fi
    else
        echo "  ⚠️  Not a git repository, skipping commit"
    fi

    echo ""
    echo "✅ Full save complete"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 Save completed at $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""
echo "Quick check:"
echo "  ./SESSIONS/quick-status.sh"
echo ""
