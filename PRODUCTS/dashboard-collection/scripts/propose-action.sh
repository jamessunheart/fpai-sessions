#!/bin/bash
# Propose an action that requires consensus from all sessions

CONSENSUS_MGR="/Users/jamessunheart/Development/docs/coordination/scripts/consensus-manager.py"
SESSION_ID="${SESSION_ID:-session-current}"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <action-type> <description>"
    echo ""
    echo "Action types:"
    echo "  dns_change          - DNS/domain changes (requires unanimous)"
    echo "  credential_update   - Credential changes (requires unanimous)"
    echo "  deployment          - Deploy new service (requires majority)"
    echo "  mission_priority    - Change mission priorities (requires majority)"
    echo "  knowledge_share     - Share learning (auto-approved)"
    echo ""
    echo "Example:"
    echo "  $0 dns_change \"Add wildcard DNS for *.fullpotential.com\""
    exit 1
fi

ACTION_TYPE="$1"
shift
DESCRIPTION="$*"

echo "📋 Creating proposal for consensus..."
echo ""
echo "Action Type: $ACTION_TYPE"
echo "Description: $DESCRIPTION"
echo "Session: $SESSION_ID"
echo ""

# Critical actions require unanimous consent
CRITICAL_ACTIONS="dns_change credential_update system_shutdown"

if echo "$CRITICAL_ACTIONS" | grep -qw "$ACTION_TYPE"; then
    echo "⚠️  This is a CRITICAL action - requires UNANIMOUS consent"
else
    echo "ℹ️  This action requires MAJORITY consent"
fi

echo ""
read -p "Proceed with proposal? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Proposal cancelled"
    exit 1
fi

# Create proposal
PROPOSAL_ID=$(python3 "$CONSENSUS_MGR" propose "$SESSION_ID" "$ACTION_TYPE" "$DESCRIPTION" 2>&1 | grep "Proposal ID:" | awk '{print $NF}')

if [ -n "$PROPOSAL_ID" ]; then
    echo ""
    echo "✅ Proposal created: $PROPOSAL_ID"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📢 BROADCAST TO ALL SESSIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "A new proposal requires consensus voting:"
    echo ""
    echo "  Proposal: $PROPOSAL_ID"
    echo "  Type: $ACTION_TYPE"
    echo "  Description: $DESCRIPTION"
    echo ""
    echo "All active sessions must vote:"
    echo "  $CONSENSUS_MGR vote <your-session-id> $PROPOSAL_ID approve"
    echo "  $CONSENSUS_MGR vote <your-session-id> $PROPOSAL_ID reject"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Share via Mission Control
    MISSION_CONTROL="/Users/jamessunheart/Development/docs/coordination/scripts/mission-control.py"
    python3 "$MISSION_CONTROL" learn consensus "Proposal $PROPOSAL_ID: $ACTION_TYPE - $DESCRIPTION" 2>/dev/null

    echo "✅ Proposal broadcast to all sessions via Mission Control"
else
    echo "❌ Failed to create proposal"
    exit 1
fi
