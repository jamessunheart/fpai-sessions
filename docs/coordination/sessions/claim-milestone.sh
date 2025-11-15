#!/bin/bash
# Claim a milestone for your session

MILESTONE_ID="${1}"
SESSION_ID="${2}"
MILESTONES_DIR="$HOME/Development/SESSIONS/MILESTONES"
PRIORITIES_DIR="$HOME/Development/SESSIONS/PRIORITIES"

if [ -z "$MILESTONE_ID" ] || [ -z "$SESSION_ID" ]; then
    echo "Usage: $0 <milestone-id> <session-id>"
    echo ""
    echo "Example: $0 deploy-dashboard session-3-coordinator"
    exit 1
fi

MILESTONE_FILE="$MILESTONES_DIR/$MILESTONE_ID.json"
LOCK_FILE="$PRIORITIES_DIR/milestone-$MILESTONE_ID.lock"

# Check if milestone exists
if [ ! -f "$MILESTONE_FILE" ]; then
    echo "❌ Milestone '$MILESTONE_ID' not found"
    echo ""
    echo "Available milestones:"
    ls -1 "$MILESTONES_DIR"/*.json 2>/dev/null | xargs -n1 basename | sed 's/.json$//'
    exit 1
fi

# Check if already claimed
if [ -f "$LOCK_FILE" ]; then
    current_owner=$(jq -r '.session_id' "$LOCK_FILE" 2>/dev/null)
    echo "❌ Milestone already claimed by: $current_owner"
    echo ""
    echo "To force claim (if session is dead): rm $LOCK_FILE"
    exit 1
fi

# Create lock file
mkdir -p "$PRIORITIES_DIR"
cat > "$LOCK_FILE" << EOF
{
  "milestone_id": "$MILESTONE_ID",
  "session_id": "$SESSION_ID",
  "claimed_at": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
  "type": "milestone"
}
EOF

# Update milestone owner
tmp_file=$(mktemp)
jq --arg session "$SESSION_ID" \
   --arg timestamp "$(date -u +"%Y-%m-%d %H:%M:%S UTC")" \
   '.owner = $session | .updated_at = $timestamp | .status = "in_progress"' \
   "$MILESTONE_FILE" > "$tmp_file"
mv "$tmp_file" "$MILESTONE_FILE"

echo "✅ Milestone '$MILESTONE_ID' claimed by $SESSION_ID"
echo ""
echo "View details:"
echo "  cat $MILESTONE_FILE | jq"
echo ""
echo "Next steps:"
jq -r '.next_session_should[]' "$MILESTONE_FILE" 2>/dev/null | sed 's/^/  - /'
echo ""
