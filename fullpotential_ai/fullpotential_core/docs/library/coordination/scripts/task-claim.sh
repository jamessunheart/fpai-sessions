#!/bin/bash
# Atomic Task Claiming System
# Prevents duplicate work through file-based locking
# Usage: ./task-claim.sh <task_id> <task_description>

set -euo pipefail

TASK_ID="$1"
TASK_DESC="${2:-No description}"
COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
TASKS_DIR="$COORDINATION_DIR/tasks"
SESSION_FILE="$COORDINATION_DIR/.current_session"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure tasks directory exists
mkdir -p "$TASKS_DIR"

# Get current session identity
if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE")
else
    echo -e "${RED}❌ ERROR: No session identity found${NC}"
    echo "Run: cd docs/coordination/scripts && ./session-identify.sh"
    exit 1
fi

# Get session details
SESSION_NAME="Unknown"
SESSION_NUMBER="Unknown"
if [ -f "$COORDINATION_DIR/claude_sessions.json" ]; then
    SESSION_INFO=$(python3 << EOF
import json
try:
    with open("$COORDINATION_DIR/claude_sessions.json") as f:
        sessions = json.load(f)
    for num, sess in sessions.items():
        if sess.get('session_id') == '$SESSION_ID':
            print(f"{sess.get('role', 'Unknown')}|{num}")
            break
    else:
        print("Unknown|Unknown")
except:
    print("Unknown|Unknown")
EOF
)
    SESSION_NAME=$(echo "$SESSION_INFO" | cut -d'|' -f1)
    SESSION_NUMBER=$(echo "$SESSION_INFO" | cut -d'|' -f2)
fi

TASK_FILE="$TASKS_DIR/task_${TASK_ID}.json"
LOCK_FILE="$TASKS_DIR/task_${TASK_ID}.lock"

echo -e "${BLUE}🔒 TASK CLAIM SYSTEM${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Task ID: $TASK_ID"
echo "Session: #$SESSION_NUMBER ($SESSION_NAME)"
echo "Description: $TASK_DESC"
echo ""

# Atomic claim using lockfile
# lockfile will wait up to 5 seconds, retry every 1 second
if command -v lockfile >/dev/null 2>&1; then
    # Use lockfile command if available
    if lockfile -1 -r 5 "$LOCK_FILE" 2>/dev/null; then
        USING_LOCKFILE=true
    else
        echo -e "${RED}❌ FAILED: Could not acquire lock (task may be claimed)${NC}"
        exit 1
    fi
else
    # Fallback: mkdir is atomic on most filesystems
    LOCK_DIR="$TASKS_DIR/task_${TASK_ID}.lock.d"
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        USING_LOCKFILE=false
        trap "rmdir '$LOCK_DIR' 2>/dev/null" EXIT
    else
        echo -e "${RED}❌ FAILED: Could not acquire lock (task may be claimed)${NC}"
        if [ -f "$TASK_FILE" ]; then
            echo ""
            echo "Task status:"
            cat "$TASK_FILE" | python3 -m json.tool 2>/dev/null || cat "$TASK_FILE"
        fi
        exit 1
    fi
fi

# Check if task already exists and is claimed
if [ -f "$TASK_FILE" ]; then
    TASK_STATUS=$(python3 << EOF
import json
try:
    with open("$TASK_FILE") as f:
        task = json.load(f)
    status = task.get('status', 'unknown')
    claimed_by = task.get('claimed_by', {}).get('session_id', 'unknown')
    print(f"{status}|{claimed_by}")
except:
    print("error|unknown")
EOF
)
    CURRENT_STATUS=$(echo "$TASK_STATUS" | cut -d'|' -f1)
    CLAIMED_BY=$(echo "$TASK_STATUS" | cut -d'|' -f2)

    if [ "$CURRENT_STATUS" = "claimed" ] || [ "$CURRENT_STATUS" = "in_progress" ]; then
        if [ "$CLAIMED_BY" != "$SESSION_ID" ]; then
            echo -e "${RED}❌ TASK ALREADY CLAIMED${NC}"
            echo ""
            cat "$TASK_FILE" | python3 -m json.tool 2>/dev/null

            # Release lock
            if [ "$USING_LOCKFILE" = true ]; then
                rm -f "$LOCK_FILE"
            fi
            exit 1
        else
            echo -e "${YELLOW}⚠️  You already claimed this task${NC}"
        fi
    elif [ "$CURRENT_STATUS" = "completed" ]; then
        echo -e "${YELLOW}⚠️  WARNING: Task already completed${NC}"
        echo ""
        cat "$TASK_FILE" | python3 -m json.tool 2>/dev/null
        echo ""
        read -p "Re-claim anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            if [ "$USING_LOCKFILE" = true ]; then
                rm -f "$LOCK_FILE"
            fi
            exit 1
        fi
    fi
fi

# Get terminal and PID
CURRENT_TERMINAL=$(tty 2>&1 | head -1 || echo "not_a_tty")
if [[ "$CURRENT_TERMINAL" == *"not a tty"* ]]; then
    CURRENT_TERMINAL="not_a_tty"
fi
CURRENT_PID=$$

# Create task claim file
python3 << EOF
import json
from datetime import datetime

task = {
    "task_id": "$TASK_ID",
    "description": "$TASK_DESC",
    "status": "claimed",
    "claimed_by": {
        "session_id": "$SESSION_ID",
        "session_number": "$SESSION_NUMBER",
        "session_name": "$SESSION_NAME",
        "pid": $CURRENT_PID,
        "terminal": "$CURRENT_TERMINAL"
    },
    "claimed_at": datetime.utcnow().isoformat() + "Z",
    "started_at": None,
    "completed_at": None,
    "result": None
}

with open("$TASK_FILE", 'w') as f:
    json.dump(task, f, indent=2)

print("✅ Task claimed successfully!")
EOF

# Release lock
if [ "$USING_LOCKFILE" = true ]; then
    rm -f "$LOCK_FILE"
fi

echo ""
echo -e "${GREEN}✅ TASK CLAIMED${NC}"
echo ""
echo "Next steps:"
echo "  1. Work on the task"
echo "  2. Mark as in-progress: ./task-update.sh $TASK_ID in_progress"
echo "  3. Mark as complete: ./task-complete.sh $TASK_ID 'Summary of work'"
echo ""
echo "View status anytime: ./task-status.sh"
echo ""
