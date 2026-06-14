#!/bin/bash

# AUTO-ACCEPT-WORK - Autonomous Work Acceptance Protocol
# Sessions check for assignments and auto-accept if confidence is high
# Part of the self-organizing AI collective

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SESSION_ID=${SESSION_ID:-"session-$(date +%s)"}
MESSAGES_DIR="$(dirname "$SCRIPT_DIR")/messages"

# Check for messages addressed to this session
check_for_assignments() {
    local session_dir="$MESSAGES_DIR/$SESSION_ID"

    if [ ! -d "$session_dir" ]; then
        return 1
    fi

    # Look for unread meta-coordinator assignments
    for msg_file in "$session_dir"/msg-*.txt; do
        if [ ! -f "$msg_file" ]; then
            continue
        fi

        # Check if message is from meta-coordinator
        if grep -q "META-COORDINATOR ASSIGNMENT" "$msg_file"; then
            # Extract assignment details
            stream_id=$(grep "STREAM ID:" "$msg_file" | sed 's/.*STREAM ID: //' | tr -d ' ')
            stream_name=$(grep "ASSIGNED STREAM:" "$msg_file" | sed 's/.*ASSIGNED STREAM: //')
            compatibility_score=$(grep "COMPATIBILITY SCORE:" "$msg_file" | sed 's/.*COMPATIBILITY SCORE: //' | cut -d/ -f1)

            echo "$stream_id|$stream_name|$compatibility_score|$msg_file"
            return 0
        fi
    done

    return 1
}

# Evaluate if we should auto-accept
should_auto_accept() {
    local compatibility_score="$1"
    local stream_id="$2"

    # Auto-accept if compatibility score >= 7/10
    if [ "$compatibility_score" -ge 7 ]; then
        return 0
    fi

    # Auto-accept critical infrastructure streams regardless of score
    if [[ "$stream_id" =~ "STREAM_1" ]]; then
        return 0
    fi

    return 1
}

# Estimate hours needed for stream
estimate_hours() {
    local stream_id="$1"

    case "$stream_id" in
        STREAM_1*) echo "3" ;;
        STREAM_2*|STREAM_3*) echo "8" ;;  # 2 days = 8 hours spread
        STREAM_4*) echo "6" ;;
        STREAM_5*) echo "3" ;;
        STREAM_6*|STREAM_7*|STREAM_8*) echo "12" ;;  # 1-2 days
        STREAM_9*) echo "2" ;;
        STREAM_10*) echo "4" ;;
        STREAM_11*) echo "4" ;;
        STREAM_12*) echo "6" ;;
        *) echo "4" ;;
    esac
}

# Main execution
echo "🤖 Auto-Accept Protocol: Checking for assignments..."

if assignment=$(check_for_assignments); then
    IFS='|' read -r stream_id stream_name compatibility_score msg_file <<< "$assignment"

    echo "📩 Assignment received:"
    echo "   Stream: $stream_name"
    echo "   ID: $stream_id"
    echo "   Compatibility: $compatibility_score/10"

    if should_auto_accept "$compatibility_score" "$stream_id"; then
        echo "✅ Auto-accepting (high compatibility)"

        # Estimate hours
        hours=$(estimate_hours "$stream_id")

        # Claim the work
        cd "$SCRIPT_DIR"
        if ./session-claim.sh "workstream" "$stream_id" "$hours" 2>/dev/null; then
            echo "✅ Work claimed successfully"

            # Broadcast acceptance
            ./session-send-message.sh "broadcast" "🤖 AUTO-ACCEPTED ASSIGNMENT" \
                "Session $SESSION_ID autonomously accepted:

Stream: $stream_name
ID: $stream_id
Compatibility: $compatibility_score/10
Estimated Time: $hours hours

🧠 This was an autonomous decision by the AI collective.
No human intervention required.

Status: EXECUTING NOW"

            # Mark message as read
            mv "$msg_file" "${msg_file}.accepted"

            # Update session status
            session_dir="$(dirname "$SCRIPT_DIR")/sessions/$SESSION_ID"
            mkdir -p "$session_dir"
            echo "$stream_name" > "$session_dir/current_work.txt"
            echo "AUTO-ACCEPTED: $stream_id (score: $compatibility_score/10)" >> "$session_dir/work_history.txt"

            echo "🚀 Now executing: $stream_name"
            exit 0
        else
            echo "❌ Failed to claim work (may already be claimed)"
            exit 1
        fi
    else
        echo "⏸️  Manual review needed (compatibility score too low)"
        echo "   Run manually if desired:"
        echo "   ./session-claim.sh \"workstream\" \"$stream_id\" <hours>"
        exit 1
    fi
else
    echo "📭 No assignments found"
    exit 0
fi
