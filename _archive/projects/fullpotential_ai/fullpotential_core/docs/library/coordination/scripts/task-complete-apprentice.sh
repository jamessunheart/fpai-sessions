#!/bin/bash
# Log apprentice task completion

if [ $# -lt 5 ]; then
    echo "Usage: ./task-complete-apprentice.sh <task_number> <apprentice_id> <status> <payment> <quality>"
    echo ""
    echo "Arguments:"
    echo "  task_number   - Task number (1-10)"
    echo "  apprentice_id - Apprentice ID (e.g., upwork_jane_smith)"
    echo "  status        - completed|needs_revision"
    echo "  payment       - Payment amount (e.g., \$50)"
    echo "  quality       - Quality rating 1-5"
    echo ""
    echo "Example:"
    echo "  ./task-complete-apprentice.sh 1 upwork_jane_smith completed \$50 5"
    exit 1
fi

TASK_NUMBER=$1
APPRENTICE_ID=$2
STATUS=$3
PAYMENT=$4
QUALITY=$5
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TASK_ID="TASK-$TASK_NUMBER-$(date -u +%Y%m%d)"

# Get task title from APPRENTICE_TASKS.md (simplified - just showing concept)
TASK_TITLE="Task #$TASK_NUMBER"

echo "Logging task completion:"
echo "  Task: $TASK_TITLE"
echo "  Apprentice: $APPRENTICE_ID"
echo "  Status: $STATUS"
echo "  Payment: $PAYMENT"
echo "  Quality: $QUALITY/5"
echo ""

# Create log entry
cat << EOF
Add this to APPRENTICE_TRACKING.json under 'task_log':

  {
    "task_id": "$TASK_ID",
    "task_number": $TASK_NUMBER,
    "title": "$TASK_TITLE",
    "claimed_by": "$APPRENTICE_ID",
    "claimed_at": "$TIMESTAMP",
    "started_at": "$TIMESTAMP",
    "completed_at": "$TIMESTAMP",
    "reviewed_at": "$TIMESTAMP",
    "status": "$STATUS",
    "payment": "$PAYMENT",
    "bonus": "\$0",
    "deliverables": ["See task submission"],
    "quality_rating": $QUALITY,
    "notes": "Logged via script"
  }

EOF

if [ "$STATUS" = "completed" ]; then
    echo "✅ Task completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Update apprentice's 'tasks_completed' count"
    echo "2. Update apprentice's 'total_earned' (+$PAYMENT)"
    echo "3. Check if tier advancement (3/10/25 tasks threshold)"
    echo "4. Release Upwork milestone"
else
    echo "⚠️  Task needs revision"
    echo ""
    echo "Next steps:"
    echo "1. Provide feedback to apprentice"
    echo "2. Update task status when resubmitted"
fi
