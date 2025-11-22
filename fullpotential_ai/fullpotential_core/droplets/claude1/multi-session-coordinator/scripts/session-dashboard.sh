#!/bin/bash
# Session Dashboard - Visual overview of unified consciousness

MISSION_CONTROL="/Users/jamessunheart/Development/docs/coordination/scripts/mission-control.py"

clear
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        🎯 UNIFIED SESSION CONTROL - MISSION DASHBOARD         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Get current mission
python3 "$MISSION_CONTROL" status 2>/dev/null | python3 << 'EOF'
import json, sys
try:
    data = json.load(sys.stdin)
    mission = data.get('active_missions', {})

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔥 HIGHEST PRIORITY MISSION")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Mission:     {mission.get('mission', 'N/A').replace('_', ' ').title()}")
    print(f"Priority:    {mission.get('priority_score', 0)} (U:{mission.get('urgency',0)} × I:{mission.get('impact',0)} × F:{mission.get('feasibility',0)})")
    print(f"Description: {mission.get('description', 'N/A')}")
    print()

except Exception as e:
    print(f"Error: {e}")
EOF

# Show recent learnings
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 RECENT CROSS-SESSION LEARNINGS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

KNOWLEDGE_FILE="/Users/jamessunheart/Development/docs/coordination/consciousness/unified_knowledge.json"
if [ -f "$KNOWLEDGE_FILE" ]; then
    cat "$KNOWLEDGE_FILE" | python3 << 'EOF'
import json, sys
try:
    knowledge = json.load(sys.stdin)
    count = 0
    for category, items in knowledge.items():
        for item in sorted(items, key=lambda x: x.get('timestamp', ''), reverse=True)[:2]:
            print(f"• [{category}] {item.get('learning', 'N/A')[:70]}")
            count += 1
            if count >= 5:
                break
        if count >= 5:
            break
    if count == 0:
        print("  (No learnings yet)")
except Exception as e:
    print(f"  Error: {e}")
EOF
else
    echo "  (Knowledge base initializing...)"
fi

echo ""

# Show active sessions
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔗 ACTIVE SESSIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SESSIONS_FILE="/Users/jamessunheart/Development/docs/coordination/consciousness/active_sessions.json"
if [ -f "$SESSIONS_FILE" ]; then
    cat "$SESSIONS_FILE" | python3 << 'EOF'
import json, sys, datetime
try:
    sessions = json.load(sys.stdin)
    if sessions:
        for sid, data in sessions.items():
            mission = data.get('assigned_mission', {}).get('mission', 'N/A')
            started = data.get('started_at', 'N/A')[:19]
            status = data.get('status', 'unknown')
            print(f"• {sid}")
            print(f"  Mission: {mission.replace('_', ' ').title()}")
            print(f"  Started: {started}")
            print(f"  Status: {status.upper()}")
            print()
    else:
        print("  (No active sessions)")
except Exception as e:
    print(f"  Error: {e}")
EOF
else
    echo "  (No sessions file yet)"
fi

# System stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SYSTEM STATS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Count knowledge items
KNOWLEDGE_COUNT=0
if [ -f "$KNOWLEDGE_FILE" ]; then
    KNOWLEDGE_COUNT=$(cat "$KNOWLEDGE_FILE" | python3 -c "import json, sys; k=json.load(sys.stdin); print(sum(len(v) for v in k.values()))" 2>/dev/null || echo "0")
fi

# Count sessions
SESSION_COUNT=0
if [ -f "$SESSIONS_FILE" ]; then
    SESSION_COUNT=$(cat "$SESSIONS_FILE" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
fi

# Count priorities
PRIORITIES_FILE="/Users/jamessunheart/Development/docs/coordination/consciousness/mission_priorities.json"
MISSION_COUNT=0
if [ -f "$PRIORITIES_FILE" ]; then
    MISSION_COUNT=$(cat "$PRIORITIES_FILE" | python3 -c "import json, sys; print(len(json.load(sys.stdin).get('missions', [])))" 2>/dev/null || echo "0")
fi

echo "Knowledge Base:     $KNOWLEDGE_COUNT learnings"
echo "Active Missions:    $MISSION_COUNT priorities"
echo "Active Sessions:    $SESSION_COUNT connected"
echo "Last Sync:          $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ QUICK COMMANDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Share learning:     $MISSION_CONTROL learn <category> \"<text>\""
echo "Sync consciousness: ./consciousness-sync.sh"
echo "Start new session:  ./unified-session-start.sh <context>"
echo "View all missions:  cat $PRIORITIES_FILE | jq '.missions'"
echo ""
