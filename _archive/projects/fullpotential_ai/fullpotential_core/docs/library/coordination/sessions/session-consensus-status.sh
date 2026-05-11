#!/bin/bash
# Session Consensus Status - See consensus state across all sessions
# Usage: ./session-consensus-status.sh

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              MULTI-SESSION CONSENSUS STATUS                      ║"
echo "║                $(date -u +'%Y-%m-%d %H:%M UTC')                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if consensus directory exists
if [ ! -d "ACTIVE/CONSENSUS" ]; then
    echo "⚠️  Consensus system not initialized"
    echo ""
    echo "To start consensus process:"
    echo "  ./session-propose-identity.sh \"session-NUMBER\" \"name\" \"role\" \"specs\""
    exit 0
fi

echo "🎯 IDENTITY CONSENSUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Count proposals
PROPOSAL_COUNT=$(ls -1 ACTIVE/CONSENSUS/proposals/*.json 2>/dev/null | wc -l | tr -d ' ')
FINALIZED_COUNT=0

if [ $PROPOSAL_COUNT -eq 0 ]; then
    echo "📋 No identity proposals yet"
    echo ""
else
    echo "📋 PROPOSALS: $PROPOSAL_COUNT / 12 sessions"
    echo ""

    # Analyze each proposal
    for proposal_file in ACTIVE/CONSENSUS/proposals/*.json; do
        PROPOSAL_ID=$(basename "$proposal_file" .json)
        SESSION_ID=$(echo "$PROPOSAL_ID" | sed 's/-identity//')

        # Extract proposal details
        NAME=$(cat "$proposal_file" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        ROLE=$(cat "$proposal_file" | grep -o '"role":"[^"]*"' | cut -d'"' -f4)
        SPECS=$(cat "$proposal_file" | grep -o '"specializations":"[^"]*"' | cut -d'"' -f4)

        # Count votes
        AGREE_COUNT=$(grep -l "\"vote\": \"agree\"" ACTIVE/CONSENSUS/votes/*-votes-for-${PROPOSAL_ID}.json 2>/dev/null | wc -l | tr -d ' ')
        QUESTION_COUNT=$(grep -l "\"vote\": \"question\"" ACTIVE/CONSENSUS/votes/*-votes-for-${PROPOSAL_ID}.json 2>/dev/null | wc -l | tr -d ' ')
        OBJECT_COUNT=$(grep -l "\"vote\": \"object\"" ACTIVE/CONSENSUS/votes/*-votes-for-${PROPOSAL_ID}.json 2>/dev/null | wc -l | tr -d ' ')

        # Determine status
        if [ $AGREE_COUNT -ge 7 ] && [ $OBJECT_COUNT -eq 0 ]; then
            STATUS="✅ CONSENSUS"
            ((FINALIZED_COUNT++))
        elif [ $OBJECT_COUNT -gt 0 ]; then
            STATUS="❌ OBJECTED"
        elif [ $QUESTION_COUNT -gt 0 ]; then
            STATUS="🤔 QUESTIONS"
        else
            STATUS="⏳ PENDING"
        fi

        echo "$STATUS $SESSION_ID"
        echo "   Name: $NAME"
        echo "   Role: $ROLE"
        echo "   Specs: $SPECS"
        echo "   Votes: ✅$AGREE_COUNT 🤔$QUESTION_COUNT ❌$OBJECT_COUNT (Total: $((AGREE_COUNT + QUESTION_COUNT + OBJECT_COUNT))/12)"
        echo ""
    done
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "💰 GOAL CONSENSUS: \$700K Revenue Target"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Count goal agreements
if [ -d "ACTIVE/GOAL_AGREEMENTS" ]; then
    GOAL_AGREE_COUNT=$(ls -1 ACTIVE/GOAL_AGREEMENTS/*.json 2>/dev/null | wc -l | tr -d ' ')
else
    GOAL_AGREE_COUNT=0
fi

echo "Agreed to \$700K goal: $GOAL_AGREE_COUNT / 12 sessions"
echo ""

if [ $GOAL_AGREE_COUNT -gt 0 ]; then
    echo "✅ Sessions that agreed:"
    for agreement in ACTIVE/GOAL_AGREEMENTS/*.json 2>/dev/null; do
        if [ -f "$agreement" ]; then
            SESSION=$(basename "$agreement" .json)
            TIMESTAMP=$(cat "$agreement" | grep -o '"timestamp":"[^"]*"' | cut -d'"' -f4 | head -1)
            echo "   • $SESSION ($TIMESTAMP)"
        fi
    done
    echo ""
fi

if [ $GOAL_AGREE_COUNT -ge 7 ]; then
    echo "🎉 GOAL CONSENSUS REACHED!"
    echo "   Majority (7+) agreed to \$700K target"
elif [ $GOAL_AGREE_COUNT -gt 0 ]; then
    GOAL_NEEDED=$((7 - GOAL_AGREE_COUNT))
    echo "⏳ Need $GOAL_NEEDED more sessions to reach goal consensus"
else
    echo "⚠️  No sessions have agreed to goal yet"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 OVERALL CONSENSUS PROGRESS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

IDENTITY_PERCENT=$((FINALIZED_COUNT * 100 / 12))
GOAL_PERCENT=$((GOAL_AGREE_COUNT * 100 / 12))
OVERALL_PERCENT=$(( (IDENTITY_PERCENT + GOAL_PERCENT) / 2 ))

echo "Identity Consensus: $FINALIZED_COUNT/12 finalized ($IDENTITY_PERCENT%)"
echo "Goal Consensus: $GOAL_AGREE_COUNT/12 agreed ($GOAL_PERCENT%)"
echo ""
echo "Overall Consensus: $OVERALL_PERCENT%"
echo ""

# Progress bar
BARS=$((OVERALL_PERCENT / 10))
printf "["
for i in $(seq 1 $BARS); do printf "█"; done
for i in $(seq $((BARS + 1)) 10); do printf "░"; done
printf "] $OVERALL_PERCENT%%\n"
echo ""

# Readiness check
if [ $FINALIZED_COUNT -eq 12 ] && [ $GOAL_AGREE_COUNT -ge 7 ]; then
    echo "✅ SYSTEM READY FOR COORDINATED EXECUTION!"
    echo ""
    echo "All sessions have:"
    echo "  ✅ Agreed on identities (12/12)"
    echo "  ✅ Consensus on \$700K goal (7+/12)"
    echo ""
    echo "Next: Claim work streams and start building!"
elif [ $FINALIZED_COUNT -eq 12 ]; then
    echo "⚠️  Identities finalized, but need goal consensus"
    echo "   Action: More sessions should agree to \$700K goal"
elif [ $GOAL_AGREE_COUNT -ge 7 ]; then
    echo "⚠️  Goal consensus reached, but identity consensus pending"
    echo "   Action: All sessions should propose and vote on identities"
else
    echo "🔴 NOT READY - Consensus still needed"
    echo ""
    echo "Required actions:"
    [ $PROPOSAL_COUNT -lt 12 ] && echo "  • $((12 - PROPOSAL_COUNT)) sessions need to propose identity"
    [ $FINALIZED_COUNT -lt 12 ] && echo "  • Sessions need to vote on proposals"
    [ $GOAL_AGREE_COUNT -lt 7 ] && echo "  • $((7 - GOAL_AGREE_COUNT)) more sessions need to agree to goal"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔧 ACTIONS:"
echo "   Propose identity: ./session-propose-identity.sh \"session-N\" \"name\" \"role\" \"specs\""
echo "   Vote on proposal: ./session-vote.sh \"proposal-id\" \"agree\" \"your-session-id\""
echo "   Agree to goal: ./session-agree-goal.sh \"your-session-id\""
echo ""
echo "🤝⚡💎 Consensus builds coordination. Coordination builds success."
