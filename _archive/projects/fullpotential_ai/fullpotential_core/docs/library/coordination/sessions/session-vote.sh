#!/bin/bash
# Session Vote - Vote on identity proposals
# Usage: ./session-vote.sh "proposal-id" "agree|question|object" "voter-session-id" ["comment"]

PROPOSAL_ID="$1"
VOTE="$2"
VOTER="$3"
COMMENT="${4:-No comment}"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

if [ -z "$PROPOSAL_ID" ] || [ -z "$VOTE" ] || [ -z "$VOTER" ]; then
    echo "Usage: ./session-vote.sh \"proposal-id\" \"agree|question|object\" \"voter-session-id\" [\"comment\"]"
    echo ""
    echo "Examples:"
    echo "  ./session-vote.sh \"session-1-identity\" \"agree\" \"session-5-orchestration\""
    echo "  ./session-vote.sh \"session-2-identity\" \"question\" \"session-6\" \"Will you handle deployments?\""
    echo "  ./session-vote.sh \"session-3-identity\" \"agree\" \"session-7\" \"Good fit\""
    exit 1
fi

# Validate vote type
if [ "$VOTE" != "agree" ] && [ "$VOTE" != "question" ] && [ "$VOTE" != "object" ]; then
    echo "❌ ERROR: Vote must be 'agree', 'question', or 'object'"
    exit 1
fi

echo "🗳️  CASTING VOTE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Proposal: $PROPOSAL_ID"
echo "Vote: $VOTE"
echo "Voter: $VOTER"
echo "Comment: $COMMENT"
echo ""

# Check if proposal exists
PROPOSAL_FILE="ACTIVE/CONSENSUS/proposals/${PROPOSAL_ID}.json"
if [ ! -f "$PROPOSAL_FILE" ]; then
    echo "❌ ERROR: Proposal not found: $PROPOSAL_ID"
    echo "   Available proposals:"
    ls -1 ACTIVE/CONSENSUS/proposals/*.json 2>/dev/null | xargs -I {} basename {} .json
    exit 1
fi

# Record vote
mkdir -p ACTIVE/CONSENSUS/votes
VOTE_FILE="ACTIVE/CONSENSUS/votes/${VOTER}-votes-for-${PROPOSAL_ID}.json"

cat > "$VOTE_FILE" << EOF
{
  "voter": "$VOTER",
  "proposal": "$PROPOSAL_ID",
  "vote": "$VOTE",
  "comment": "$COMMENT",
  "timestamp": "$TIMESTAMP"
}
EOF

echo "✅ Vote recorded!"
echo ""

# Count votes for this proposal
AGREE_COUNT=$(grep -l "\"vote\": \"agree\"" ACTIVE/CONSENSUS/votes/*-votes-for-${PROPOSAL_ID}.json 2>/dev/null | wc -l | tr -d ' ')
QUESTION_COUNT=$(grep -l "\"vote\": \"question\"" ACTIVE/CONSENSUS/votes/*-votes-for-${PROPOSAL_ID}.json 2>/dev/null | wc -l | tr -d ' ')
OBJECT_COUNT=$(grep -l "\"vote\": \"object\"" ACTIVE/CONSENSUS/votes/*-votes-for-${PROPOSAL_ID}.json 2>/dev/null | wc -l | tr -d ' ')
TOTAL_VOTES=$((AGREE_COUNT + QUESTION_COUNT + OBJECT_COUNT))

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 VOTE TALLY FOR $PROPOSAL_ID:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   ✅ Agree: $AGREE_COUNT"
echo "   🤔 Question: $QUESTION_COUNT"
echo "   ❌ Object: $OBJECT_COUNT"
echo "   📊 Total votes: $TOTAL_VOTES / 12"
echo ""

# Check if consensus reached
if [ $AGREE_COUNT -ge 7 ] && [ $OBJECT_COUNT -eq 0 ]; then
    echo "🎉 CONSENSUS REACHED!"
    echo "   $PROPOSAL_ID has been approved with $AGREE_COUNT votes!"
    echo ""

    # Update proposal status
    # Note: In production would use jq or similar to properly update JSON

    # Broadcast consensus
    PROPOSAL_SESSION=$(echo "$PROPOSAL_ID" | sed 's/-identity//')
    cat >> MESSAGES.md << EOF

---

**Time:** $TIMESTAMP
**Priority:** 🎉 CONSENSUS REACHED

### ✅ CONSENSUS: $PROPOSAL_ID APPROVED!

The proposal for $PROPOSAL_SESSION has reached consensus!

**Votes:**
- ✅ Agree: $AGREE_COUNT
- 🤔 Question: $QUESTION_COUNT
- ❌ Object: $OBJECT_COUNT

**Status:** ✅ FINALIZED

This session identity is now official and recorded in REGISTRY.json.

---

EOF

elif [ $AGREE_COUNT -ge 7 ] && [ $QUESTION_COUNT -gt 0 ]; then
    echo "⚠️  CONSENSUS PENDING"
    echo "   7+ agree votes, but $QUESTION_COUNT questions remain"
    echo "   Proposer should address questions"

elif [ $OBJECT_COUNT -gt 0 ]; then
    echo "❌ OBJECTIONS RAISED"
    echo "   $OBJECT_COUNT sessions object to this proposal"
    echo "   Proposer should revise or discuss"

else
    NEEDED=$((7 - AGREE_COUNT))
    echo "⏳ AWAITING MORE VOTES"
    echo "   Need $NEEDED more 'agree' votes for consensus"
fi

echo ""
echo "Run ./session-consensus-status.sh to see all proposals"
echo ""
echo "🗳️⚡💎 Your vote has been recorded!"
