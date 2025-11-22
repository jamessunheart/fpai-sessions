#!/bin/bash
# Session Goal Agreement - Formally agree to the $700K shared goal
# Usage: ./session-agree-goal.sh "session-id" ["optional comment"]

SESSION_ID="$1"
COMMENT="${2:-I agree to work toward the $700K revenue goal}"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

if [ -z "$SESSION_ID" ]; then
    echo "Usage: ./session-agree-goal.sh \"session-id\" [\"comment\"]"
    echo ""
    echo "Examples:"
    echo "  ./session-agree-goal.sh \"session-1-dashboard\""
    echo "  ./session-agree-goal.sh \"session-2-consciousness\" \"Fully aligned on revenue focus\""
    exit 1
fi

echo "🎯 GOAL AGREEMENT PROTOCOL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Session: $SESSION_ID"
echo "Goal: $700K Annual Recurring Revenue"
echo "Comment: $COMMENT"
echo "Timestamp: $TIMESTAMP"
echo ""

# Record agreement
mkdir -p ACTIVE/GOAL_AGREEMENTS
cat > "ACTIVE/GOAL_AGREEMENTS/${SESSION_ID}.json" << EOF
{
  "session_id": "$SESSION_ID",
  "goal": "$700K Annual Recurring Revenue",
  "agreed": true,
  "comment": "$COMMENT",
  "timestamp": "$TIMESTAMP",
  "commits_to": [
    "Coordination first - check CURRENT_STATE.md before work",
    "No duplicate work - use session-sync.sh",
    "Revenue focus - prioritize $700K target work",
    "Collaboration - help other sessions",
    "Quality - tests pass, UBIC compliant",
    "Autonomous progress - work toward goal proactively",
    "Shared learning - document insights",
    "Update consciousness - keep CURRENT_STATE.md fresh"
  ]
}
EOF

# Update SHARED_GOAL.md
# Note: This is a simple update - in production would parse and update properly
echo "✅ Agreement recorded in ACTIVE/GOAL_AGREEMENTS/${SESSION_ID}.json"

# Broadcast agreement
cat >> MESSAGES.md << EOF

---

**From:** $SESSION_ID
**Time:** $TIMESTAMP
**Priority:** 🎯 GOAL ALIGNMENT

### ✅ GOAL AGREEMENT: $SESSION_ID

$SESSION_ID has formally agreed to the shared $700K revenue goal!

**Comment:** $COMMENT

**Commits to:**
- Coordination first
- Revenue focus
- Quality standards
- Autonomous progress toward goal

**Agreement file:** ACTIVE/GOAL_AGREEMENTS/${SESSION_ID}.json

EOF

# Count agreements
TOTAL_AGREEMENTS=$(ls -1 ACTIVE/GOAL_AGREEMENTS/*.json 2>/dev/null | wc -l | tr -d ' ')
TOTAL_SESSIONS=12

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 AGREEMENT PROGRESS: $TOTAL_AGREEMENTS / $TOTAL_SESSIONS sessions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$TOTAL_AGREEMENTS" -eq "$TOTAL_SESSIONS" ]; then
    echo "🎉 ALL SESSIONS ALIGNED! 12x parallel capacity unlocked!"
    echo ""
    echo "Next: Execute work streams toward $700K target"
else
    REMAINING=$((TOTAL_SESSIONS - TOTAL_AGREEMENTS))
    echo "⏳ Awaiting $REMAINING more sessions to agree"
    echo ""
    echo "Sessions that agreed:"
    ls -1 ACTIVE/GOAL_AGREEMENTS/*.json 2>/dev/null | xargs -I {} basename {} .json | sed 's/^/   ✅ /'
fi

echo ""
echo "🌐⚡💎 Thank you for aligning on the shared goal!"
