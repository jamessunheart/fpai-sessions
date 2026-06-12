#!/bin/bash
# Unified Session Starter - Connects any Claude session to Mission Control

SESSION_ID="session-$(date +%s)"
MISSION_CONTROL="/Users/jamessunheart/Development/docs/coordination/scripts/mission-control.py"

echo "🎯 UNIFIED SESSION ORCHESTRATOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Session ID: $SESSION_ID"
echo ""

# Get context
CONTEXT="$1"
if [ -z "$CONTEXT" ]; then
    CONTEXT="general"
fi

# Register with Mission Control
echo "📡 Connecting to Mission Control..."
MISSION_DATA=$(python3 "$MISSION_CONTROL" start "$SESSION_ID" "$CONTEXT" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Connected to unified consciousness"
    echo ""

    echo "🎯 ASSIGNED MISSION:"
    echo "$MISSION_DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
mission = data.get('mission', {})
print(f\"  Mission: {mission.get('mission', 'N/A')}\")
print(f\"  Priority: {mission.get('priority_score', 0)}\")
print(f\"  Description: {mission.get('description', 'N/A')}\")
"
    echo ""

    echo "📚 SHARED KNOWLEDGE AVAILABLE:"
    echo "$MISSION_DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
knowledge = data.get('shared_knowledge', [])
print(f\"  {len(knowledge)} recent learnings from other sessions\")
"
    echo ""

    echo "🎯 ACTIVE GOALS:"
    echo "$MISSION_DATA" | python3 -c "
import sys, json
data = json.load(sys.stdin)
goals = data.get('active_goals', [])
for goal in goals[:3]:
    print(f\"  • {goal.get('goal', 'N/A')}\")
"
    echo ""

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Session unified and mission-directed!"
    echo ""
    echo "To share learnings across sessions:"
    echo "  $MISSION_CONTROL learn <category> \"<learning>\""
    echo ""
    echo "To sync with server consciousness:"
    echo "  $MISSION_CONTROL sync"
    echo ""

    # Save session ID for easy reference
    echo "$SESSION_ID" > /tmp/current-session-id

else
    echo "⚠️  Could not connect to Mission Control"
    echo "   Continuing in standalone mode..."
fi
