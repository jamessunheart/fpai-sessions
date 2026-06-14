#!/bin/bash
# Task Completion System
# Marks task as completed with result summary
# Usage: ./task-complete.sh <task_id> '<result_summary>'

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <task_id> '<result_summary>'"
    exit 1
fi

TASK_ID="$1"
RESULT="$2"
COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
TASKS_DIR="$COORDINATION_DIR/tasks"
SESSION_FILE="$COORDINATION_DIR/.current_session"
TASK_FILE="$TASKS_DIR/task_${TASK_ID}.json"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if task exists
if [ ! -f "$TASK_FILE" ]; then
    echo -e "${RED}❌ Task $TASK_ID not found${NC}"
    exit 1
fi

# Get current session
SESSION_ID="unknown"
if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE")
fi

# Complete task
python3 << EOF
import json
from datetime import datetime

with open("$TASK_FILE", 'r') as f:
    task = json.load(f)

claimed_by = task.get('claimed_by', {}).get('session_id')

# Verify ownership
if claimed_by and claimed_by != "$SESSION_ID":
    print("❌ ERROR: Task is claimed by another session")
    print(f"   Claimed by: {claimed_by}")
    print(f"   Your session: $SESSION_ID")
    exit(1)

# Update to completed
task['status'] = 'completed'
task['result'] = "$RESULT"

if not task.get('completed_at'):
    task['completed_at'] = datetime.utcnow().isoformat() + "Z"

# Calculate duration if started
if task.get('started_at') and task.get('completed_at'):
    try:
        started = datetime.fromisoformat(task['started_at'].replace('Z', ''))
        completed = datetime.fromisoformat(task['completed_at'].replace('Z', ''))
        duration_seconds = (completed - started).total_seconds()
        task['duration_seconds'] = int(duration_seconds)
    except:
        pass

# Save
with open("$TASK_FILE", 'w') as f:
    json.dump(task, f, indent=2)

print(f"✅ Task {task['task_id']}: {task['description']}")
print(f"📝 Result: $RESULT")

if task.get('duration_seconds'):
    duration = task['duration_seconds']
    if duration < 60:
        print(f"⏱️  Duration: {duration}s")
    elif duration < 3600:
        print(f"⏱️  Duration: {duration//60}m {duration%60}s")
    else:
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        print(f"⏱️  Duration: {hours}h {minutes}m")
EOF

echo ""
echo -e "${GREEN}✅ TASK COMPLETED${NC}"
echo ""
