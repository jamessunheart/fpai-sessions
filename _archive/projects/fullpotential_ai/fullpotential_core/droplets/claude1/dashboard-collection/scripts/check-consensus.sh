#!/bin/bash
# Check for pending consensus proposals and prompt for votes

CONSENSUS_MGR="/Users/jamessunheart/Development/docs/coordination/scripts/consensus-manager.py"
SESSION_ID="${1:-session-$(date +%s)}"

echo "🗳️  Checking for proposals requiring consensus..."
echo ""

# Get pending proposals
PENDING=$(python3 "$CONSENSUS_MGR" pending "$SESSION_ID" 2>/dev/null)

if echo "$PENDING" | grep -q "Pending Proposals: 0"; then
    echo "✅ No pending proposals"
    exit 0
fi

echo "$PENDING"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  ACTION REQUIRED: Pending proposals need your vote!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To vote on a proposal:"
echo "  $CONSENSUS_MGR vote $SESSION_ID <proposal-id> approve"
echo "  $CONSENSUS_MGR vote $SESSION_ID <proposal-id> reject"
echo "  $CONSENSUS_MGR vote $SESSION_ID <proposal-id> abstain"
echo ""
