#!/bin/bash
# Create a new milestone from template

TITLE="${1}"
PRIORITY="${2:-MEDIUM}"
SESSION_ID="${3:-available}"

MILESTONES_DIR="$HOME/Development/SESSIONS/MILESTONES"

if [ -z "$TITLE" ]; then
    echo "Usage: $0 <title> [priority] [session-id]"
    echo ""
    echo "Priority: HIGH | MEDIUM | LOW (default: MEDIUM)"
    echo ""
    echo "Example: $0 'Deploy Dashboard' HIGH session-3-coordinator"
    exit 1
fi

# Generate milestone ID from title (lowercase, spaces to dashes)
MILESTONE_ID=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
MILESTONE_FILE="$MILESTONES_DIR/$MILESTONE_ID.json"

if [ -f "$MILESTONE_FILE" ]; then
    echo "❌ Milestone '$MILESTONE_ID' already exists"
    echo ""
    echo "View it: cat $MILESTONE_FILE | jq"
    exit 1
fi

# Create milestone from template
mkdir -p "$MILESTONES_DIR"
timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

cat > "$MILESTONE_FILE" << EOF
{
  "milestone_id": "$MILESTONE_ID",
  "title": "$TITLE",
  "priority": "$PRIORITY",
  "owner": "$SESSION_ID",
  "status": "pending",
  "progress": 0,
  "created_at": "$timestamp",
  "updated_at": "$timestamp",
  "context": {
    "why": "TODO: Explain why this milestone matters",
    "timeline": "TODO: Estimated time",
    "related_files": [],
    "dependencies": [],
    "success_criteria": "TODO: What does success look like?"
  },
  "steps": [
    {
      "step": 1,
      "description": "TODO: First step",
      "status": "pending",
      "notes": ""
    },
    {
      "step": 2,
      "description": "TODO: Second step",
      "status": "pending",
      "notes": ""
    },
    {
      "step": 3,
      "description": "TODO: Third step",
      "status": "pending",
      "notes": ""
    }
  ],
  "next_session_should": [
    "TODO: Fill in the context fields",
    "TODO: Add detailed steps",
    "TODO: Start from step 1"
  ],
  "blockers": [],
  "handoff_notes": ""
}
EOF

echo "✅ Milestone created: $MILESTONE_ID"
echo ""
echo "Next steps:"
echo "  1. Edit the milestone: $MILESTONE_FILE"
echo "  2. Fill in context, steps, and success criteria"
echo "  3. Claim it: ./SESSIONS/claim-milestone.sh $MILESTONE_ID <your-session-id>"
echo ""
echo "Template created with 3 example steps. Edit as needed."
echo ""
