#!/bin/bash
# session-create-log.sh - Create work log for a session

set -e

SESSION_ID=$1
ROLE=$2
GOAL=$3

if [ -z "$SESSION_ID" ] || [ -z "$ROLE" ] || [ -z "$GOAL" ]; then
    echo "Usage: ./session-create-log.sh SESSION_ID 'Role' 'Goal'"
    echo "Example: ./session-create-log.sh session-12 'DevOps Engineer' 'Deploy and maintain services'"
    exit 1
fi

LOG_DIR="/Users/jamessunheart/Development/docs/coordination/sessions/ACTIVE"
LOG_FILE="$LOG_DIR/${SESSION_ID}.md"
TEMPLATE="/Users/jamessunheart/Development/docs/coordination/sessions/SESSION_LOG_TEMPLATE.md"

# Create ACTIVE directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Create log from template
if [ -f "$TEMPLATE" ]; then
    cp "$TEMPLATE" "$LOG_FILE"

    # Replace placeholders
    sed -i '' "s/\[ID\]/$SESSION_ID/g" "$LOG_FILE"
    sed -i '' "s/\[Your Role\]/$ROLE/g" "$LOG_FILE"
    sed -i '' "s/\[Your Goal\]/$GOAL/g" "$LOG_FILE"
    sed -i '' "s/\[Date\]/$(date '+%Y-%m-%d')/g" "$LOG_FILE"
    sed -i '' "s/\[Date Time\]/$(date '+%Y-%m-%d %H:%M:%S')/g" "$LOG_FILE"

    echo "✅ Session log created: $LOG_FILE"
    echo ""
    echo "📝 To update your log:"
    echo "   nano $LOG_FILE"
    echo ""
    echo "📊 To view your log:"
    echo "   cat $LOG_FILE"
else
    # Create basic log without template
    cat > "$LOG_FILE" << EOF
# $SESSION_ID - Work Log

**Role:** $ROLE
**Goal:** $GOAL
**Started:** $(date '+%Y-%m-%d')
**Status:** Active

---

## Current Work

Working on: [describe current task]

## Completed Today

- [ ] Task 1
- [ ] Task 2

## Learnings

[Document what you learned]

## Next Steps

[What's next]

---

**Last Updated:** $(date '+%Y-%m-%d %H:%M:%S')
EOF

    echo "✅ Session log created: $LOG_FILE"
fi
