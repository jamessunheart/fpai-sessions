#!/bin/bash
# Task Update System
# Updates task status (claimed -> in_progress -> completed)
# Usage: ./task-update.sh <task_id> <status>

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <task_id> <status>"
    echo "Status: claimed | in_progress | completed | available"
    exit 1
fi

TASK_ID="$1"
NEW_STATUS="$2"
COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
TASKS_DIR="$COORDINATION_DIR/tasks"
SESSION_FILE="$COORDINATION_DIR/.current_session"
TASK_FILE="$TASKS_DIR/task_${TASK_ID}.json"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Validate status
if [[ ! "$NEW_STATUS" =~ ^(claimed|in_progress|completed|available)$ ]]; then
    echo -e "${RED}❌ Invalid status: $NEW_STATUS${NC}"
    echo "Valid statuses: claimed, in_progress, completed, available"
    exit 1
fi

# Check if task exists
if [ ! -f "$TASK_FILE" ]; then
    echo -e "${RED}❌ Task $TASK_ID not found${NC}"
    echo "Available tasks:"
    ls -1 "$TASKS_DIR"/task_*.json 2>/dev/null | sed 's/.*task_/  /' | sed 's/.json$//' || echo "  None"
    exit 1
fi

# Get current session
SESSION_ID="unknown"
if [ -f "$SESSION_FILE" ]; then
    SESSION_ID=$(cat "$SESSION_FILE")
fi

# Update task
python3 << EOF
import json
from datetime import datetime

with open("$TASK_FILE", 'r') as f:
    task = json.load(f)

old_status = task.get('status', 'unknown')
claimed_by = task.get('claimed_by', {}).get('session_id')

# Verify ownership for status changes
if "$NEW_STATUS" != "available" and claimed_by and claimed_by != "$SESSION_ID":
    print("❌ ERROR: Task is claimed by another session")
    print(f"   Claimed by: {claimed_by}")
    print(f"   Your session: $SESSION_ID")
    exit(1)

# Update status
task['status'] = "$NEW_STATUS"

# Update timestamps
if "$NEW_STATUS" == "in_progress" and not task.get('started_at'):
    task['started_at'] = datetime.utcnow().isoformat() + "Z"
elif "$NEW_STATUS" == "completed" and not task.get('completed_at'):
    task['completed_at'] = datetime.utcnow().isoformat() + "Z"
elif "$NEW_STATUS" == "available":
    # Clear ownership
    task['claimed_by'] = None
    task['started_at'] = None
    task['completed_at'] = None

# Save
with open("$TASK_FILE", 'w') as f:
    json.dump(task, f, indent=2)

# Status emoji
emoji = {
    'available': '⭕',
    'claimed': '🔵',
    'in_progress': '🔄',
    'completed': '✅'
}.get("$NEW_STATUS", '❓')

print(f"{emoji} Task {task['task_id']} status: {old_status} → $NEW_STATUS")
EOF

echo ""
echo -e "${GREEN}✅ Task updated${NC}"
echo ""
