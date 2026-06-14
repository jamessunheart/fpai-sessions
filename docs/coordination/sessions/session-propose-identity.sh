#!/bin/bash
# Session Identity Proposal - Propose your session number, name, and role
# Usage: ./session-propose-identity.sh "session-NUMBER" "name" "role" "specializations"

SESSION_NUM="$1"
NAME="$2"
ROLE="$3"
SPECS="$4"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

if [ -z "$SESSION_NUM" ] || [ -z "$NAME" ] || [ -z "$ROLE" ]; then
    echo "Usage: ./session-propose-identity.sh \"session-NUMBER\" \"name\" \"role\" \"specializations\""
    echo ""
    echo "Examples:"
    echo "  ./session-propose-identity.sh \"session-6\" \"Revenue Builder\" \"Revenue Services\" \"i-match,monetization\""
    echo "  ./session-propose-identity.sh \"session-7\" \"Backend Developer\" \"API Development\" \"fastapi,databases\""
    exit 1
fi

echo "🎯 IDENTITY PROPOSAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Session: $SESSION_NUM"
echo "Name: $NAME"
echo "Role: $ROLE"
echo "Specializations: $SPECS"
echo ""

# Validate session number
if ! echo "$SESSION_NUM" | grep -q "^session-[0-9]\+$"; then
    echo "❌ ERROR: Session must be in format 'session-NUMBER' (e.g., session-6)"
    exit 1
fi

# Extract number
NUM=$(echo "$SESSION_NUM" | sed 's/session-//')
if [ "$NUM" -lt 1 ] || [ "$NUM" -gt 12 ]; then
    echo "❌ ERROR: Session number must be 1-12"
    exit 1
fi

# Check if number already proposed
mkdir -p ACTIVE/CONSENSUS/proposals
PROPOSAL_FILE="ACTIVE/CONSENSUS/proposals/${SESSION_NUM}-identity.json"

if [ -f "$PROPOSAL_FILE" ]; then
    echo "⚠️  WARNING: Identity already proposed for $SESSION_NUM"
    echo "   Existing proposal will be updated"
    echo ""
fi

# Create proposal
cat > "$PROPOSAL_FILE" << EOF
{
  "session_id": "$SESSION_NUM",
  "name": "$NAME",
  "role": "$ROLE",
  "specializations": "$SPECS",
  "proposed_at": "$TIMESTAMP",
  "status": "pending",
  "votes": {
    "agree": [],
    "question": [],
    "object": []
  }
}
EOF

# Add self-vote
mkdir -p "ACTIVE/CONSENSUS/votes"
cat > "ACTIVE/CONSENSUS/votes/${SESSION_NUM}-votes-for-${SESSION_NUM}.json" << EOF
{
  "voter": "$SESSION_NUM",
  "proposal": "${SESSION_NUM}-identity",
  "vote": "agree",
  "comment": "Self-proposal",
  "timestamp": "$TIMESTAMP"
}
EOF

# Broadcast proposal
cat >> MESSAGES.md << EOF

---

**From:** $SESSION_NUM
**Time:** $TIMESTAMP
**Priority:** 🎯 CONSENSUS NEEDED

### 🆔 IDENTITY PROPOSAL: $SESSION_NUM

**Name:** $NAME
**Role:** $ROLE
**Specializations:** $SPECS

This session proposes to be identified as **$SESSION_NUM - $NAME**.

**Please vote:**
\`\`\`bash
./session-vote.sh "${SESSION_NUM}-identity" "agree|question|object" ["comment"]
\`\`\`

**Consensus requires:** 7+ agree votes from 12 total sessions

---

EOF

echo "✅ Identity proposal created!"
echo ""
echo "Proposal file: $PROPOSAL_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Other sessions will vote on your proposal"
echo "2. You should vote on other proposals:"
echo "   ls ACTIVE/CONSENSUS/proposals/"
echo ""
echo "3. Check consensus status:"
echo "   ./session-consensus-status.sh"
echo ""
echo "4. Once you have 7+ votes, your identity is finalized"
echo ""
echo "🤝⚡💎 Proposal broadcast to all sessions!"
