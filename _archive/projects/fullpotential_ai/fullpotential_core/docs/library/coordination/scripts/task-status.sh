#!/bin/bash
# Task Status Viewer
# Shows all tasks and their current status
# Usage: ./task-status.sh [task_id]

COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
TASKS_DIR="$COORDINATION_DIR/tasks"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ $# -eq 1 ]; then
    # Show specific task
    TASK_ID="$1"
    TASK_FILE="$TASKS_DIR/task_${TASK_ID}.json"

    if [ ! -f "$TASK_FILE" ]; then
        echo -e "${RED}❌ Task $TASK_ID not found${NC}"
        exit 1
    fi

    echo -e "${BLUE}📋 TASK DETAILS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    cat "$TASK_FILE" | python3 -m json.tool
    exit 0
fi

# Show all tasks
echo -e "${BLUE}📋 ALL TASKS STATUS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "$TASKS_DIR" ] || [ -z "$(ls -A $TASKS_DIR/task_*.json 2>/dev/null)" ]; then
    echo "No tasks found."
    echo ""
    echo "Create a task with: ./task-claim.sh <id> '<description>'"
    exit 0
fi

python3 << 'EOF'
import json
import os
import sys
from datetime import datetime
from pathlib import Path

tasks_dir = Path(os.environ.get('TASKS_DIR', '/Users/jamessunheart/Development/docs/coordination/tasks'))

tasks = []
for task_file in sorted(tasks_dir.glob('task_*.json')):
    try:
        with open(task_file) as f:
            task = json.load(f)
            tasks.append(task)
    except Exception as e:
        print(f"Error reading {task_file}: {e}", file=sys.stderr)

if not tasks:
    print("No tasks found.")
    sys.exit(0)

# Group by status
available = []
claimed = []
in_progress = []
completed = []

for task in tasks:
    status = task.get('status', 'unknown')
    if status == 'available':
        available.append(task)
    elif status == 'claimed':
        claimed.append(task)
    elif status == 'in_progress':
        in_progress.append(task)
    elif status == 'completed':
        completed.append(task)

def format_time_ago(iso_time):
    if not iso_time:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        now = datetime.utcnow()
        delta = now - dt.replace(tzinfo=None)
        seconds = delta.total_seconds()

        if seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds/60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h ago"
        else:
            return f"{int(seconds/86400)}d ago"
    except:
        return iso_time

def print_task(task, show_details=True):
    task_id = task.get('task_id', 'unknown')
    desc = task.get('description', 'No description')
    status = task.get('status', 'unknown')

    # Status emoji
    status_emoji = {
        'available': '⭕',
        'claimed': '🔵',
        'in_progress': '🔄',
        'completed': '✅'
    }.get(status, '❓')

    print(f"  {status_emoji} Task {task_id}: {desc}")

    if show_details:
        claimed_by = task.get('claimed_by', {})
        if claimed_by:
            sess_name = claimed_by.get('session_name', 'Unknown')
            sess_num = claimed_by.get('session_number', '?')
            terminal = claimed_by.get('terminal', 'unknown')
            print(f"     👤 Session #{sess_num} ({sess_name}) on {terminal}")

        claimed_at = task.get('claimed_at')
        started_at = task.get('started_at')
        completed_at = task.get('completed_at')

        if claimed_at:
            print(f"     🕐 Claimed: {format_time_ago(claimed_at)}")
        if started_at:
            print(f"     ▶️  Started: {format_time_ago(started_at)}")
        if completed_at:
            print(f"     ✅ Completed: {format_time_ago(completed_at)}")
            result = task.get('result')
            if result:
                print(f"     📝 Result: {result}")
    print()

# Print by status
if in_progress:
    print("🔄 IN PROGRESS:")
    print()
    for task in in_progress:
        print_task(task)

if claimed:
    print("🔵 CLAIMED (not started):")
    print()
    for task in claimed:
        print_task(task)

if available:
    print("⭕ AVAILABLE:")
    print()
    for task in available:
        print_task(task, show_details=False)

if completed:
    print("✅ COMPLETED:")
    print()
    for task in completed:
        print_task(task)

# Summary
total = len(tasks)
print("━" * 50)
print(f"Total: {total} tasks ({len(in_progress)} in progress, {len(claimed)} claimed, {len(available)} available, {len(completed)} completed)")
EOF

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Commands:"
echo "  ./task-claim.sh <id> '<description>'  - Claim a task"
echo "  ./task-update.sh <id> <status>        - Update task status"
echo "  ./task-complete.sh <id> '<result>'    - Mark task complete"
echo "  ./task-status.sh <id>                 - View specific task"
echo ""
