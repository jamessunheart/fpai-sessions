#!/bin/bash
# Update milestone step status

MILESTONE_ID="${1}"
STEP_NUM="${2}"
NEW_STATUS="${3}"
NOTES="${4}"
SESSION_ID="${5:-unknown}"

MILESTONES_DIR="$HOME/Development/SESSIONS/MILESTONES"
MILESTONE_FILE="$MILESTONES_DIR/$MILESTONE_ID.json"

if [ -z "$MILESTONE_ID" ] || [ -z "$STEP_NUM" ] || [ -z "$NEW_STATUS" ]; then
    echo "Usage: $0 <milestone-id> <step-number> <status> [notes] [session-id]"
    echo ""
    echo "Status: pending | in_progress | completed | blocked"
    echo ""
    echo "Example: $0 deploy-dashboard 3 completed 'Deployment successful' session-3"
    exit 1
fi

if [ ! -f "$MILESTONE_FILE" ]; then
    echo "❌ Milestone '$MILESTONE_ID' not found"
    exit 1
fi

# Update step status
tmp_file=$(mktemp)
timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

jq --arg step "$STEP_NUM" \
   --arg status "$NEW_STATUS" \
   --arg notes "$NOTES" \
   --arg session "$SESSION_ID" \
   --arg timestamp "$timestamp" \
   '
   (.steps[] | select(.step == ($step | tonumber)) | .status) = $status |
   (.steps[] | select(.step == ($step | tonumber)) | .notes) = $notes |
   (if $status == "completed" then
      (.steps[] | select(.step == ($step | tonumber)) | .completed_by) = $session |
      (.steps[] | select(.step == ($step | tonumber)) | .completed_at) = $timestamp
    elif $status == "in_progress" then
      (.steps[] | select(.step == ($step | tonumber)) | .started_by) = $session |
      (.steps[] | select(.step == ($step | tonumber)) | .started_at) = $timestamp
    else . end) |
   .updated_at = $timestamp
   ' "$MILESTONE_FILE" > "$tmp_file"
mv "$tmp_file" "$MILESTONE_FILE"

# Recalculate progress
tmp_file=$(mktemp)
jq '
  .progress = (
    ([.steps[] | select(.status == "completed")] | length) /
    (.steps | length) * 100 | floor
  )
' "$MILESTONE_FILE" > "$tmp_file"
mv "$tmp_file" "$MILESTONE_FILE"

progress=$(jq -r '.progress' "$MILESTONE_FILE")
echo "✅ Step $STEP_NUM updated to '$NEW_STATUS'"
echo "📊 Progress: $progress%"

# Check if milestone complete
if [ "$progress" = "100" ]; then
    tmp_file=$(mktemp)
    jq '.status = "completed"' "$MILESTONE_FILE" > "$tmp_file"
    mv "$tmp_file" "$MILESTONE_FILE"
    echo "🎉 Milestone COMPLETE!"
    echo ""
    echo "Don't forget to:"
    echo "  1. Release lock: rm SESSIONS/PRIORITIES/milestone-$MILESTONE_ID.lock"
    echo "  2. Update CURRENT_STATE.md"
fi

echo ""
