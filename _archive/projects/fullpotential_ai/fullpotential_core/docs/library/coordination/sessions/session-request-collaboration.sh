#!/bin/bash
# Session Collaboration Request - Request help from another session
# Usage: ./session-request-collaboration.sh "target-session-id" "what you need" ["urgency"]

TARGET_SESSION="$1"
REQUEST="$2"
URGENCY="${3:-normal}"
MY_SESSION="${4:-session-5-orchestration}"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
REQUEST_ID="collab-$(date +%s)"

if [ -z "$TARGET_SESSION" ] || [ -z "$REQUEST" ]; then
    echo "Usage: ./session-request-collaboration.sh \"target-session\" \"request\" [urgency]"
    echo ""
    echo "Examples:"
    echo "  ./session-request-collaboration.sh \"session-1-dashboard\" \"Need UI for analytics dashboard\""
    echo "  ./session-request-collaboration.sh \"session-4-deployment\" \"Deploy new service\" \"urgent\""
    exit 1
fi

# Create collaboration request
cat >> MESSAGES.md << EOF

---

## 🤝 COLLABORATION REQUEST #$REQUEST_ID

**From:** $MY_SESSION
**To:** $TARGET_SESSION
**Time:** $TIMESTAMP
**Urgency:** $URGENCY

### Request:
$REQUEST

### How to respond:
Reply below or update your status in HEARTBEATS/${MY_SESSION}.json

**Status:** ⏳ Awaiting response

EOF

# Also create a dedicated collaboration file
mkdir -p ACTIVE/COLLABORATIONS
cat > "ACTIVE/COLLABORATIONS/$REQUEST_ID.json" << EOF
{
  "request_id": "$REQUEST_ID",
  "from_session": "$MY_SESSION",
  "to_session": "$TARGET_SESSION",
  "request": "$REQUEST",
  "urgency": "$URGENCY",
  "status": "pending",
  "created_at": "$TIMESTAMP",
  "updated_at": "$TIMESTAMP"
}
EOF

echo "✅ Collaboration request sent!"
echo "   Request ID: $REQUEST_ID"
echo "   Target: $TARGET_SESSION"
echo ""
echo "📬 $TARGET_SESSION will see this in MESSAGES.md"
echo "📁 Tracking: ACTIVE/COLLABORATIONS/$REQUEST_ID.json"
