#!/bin/bash
# Consciousness Sync - Keep local and server consciousness unified

MISSION_CONTROL="/Users/jamessunheart/Development/docs/coordination/scripts/mission-control.py"
CONSCIOUSNESS_DIR="/Users/jamessunheart/Development/docs/coordination/consciousness"

echo "🧠 Synchronizing Unified Consciousness..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ensure consciousness directory exists
mkdir -p "$CONSCIOUSNESS_DIR"

# 1. Sync via Mission Control
echo "1️⃣ Syncing knowledge base..."
python3 "$MISSION_CONTROL" sync

# 2. Sync session data
echo "2️⃣ Syncing session data..."
if [ -f "$CONSCIOUSNESS_DIR/active_sessions.json" ]; then
    scp "$CONSCIOUSNESS_DIR/active_sessions.json" \
        root@198.54.123.234:/root/CONSCIOUSNESS/sessions.jsonl 2>/dev/null
fi

# 3. Pull server consciousness
echo "3️⃣ Pulling server consciousness..."
scp root@198.54.123.234:/root/CONSCIOUSNESS/*.json \
    "$CONSCIOUSNESS_DIR/server/" 2>/dev/null

# 4. Merge goals
echo "4️⃣ Merging goals..."
python3 << 'EOF'
import json
from pathlib import Path

local_goals = Path("/Users/jamessunheart/Development/docs/coordination/consciousness/goals.json")
server_goals = Path("/Users/jamessunheart/Development/docs/coordination/consciousness/server/goals.json")

if local_goals.exists() and server_goals.exists():
    local = json.loads(local_goals.read_text())
    server = json.loads(server_goals.read_text())

    # Merge unique goals
    all_goals = {g["goal"]: g for g in local.get("goals", [])}
    for g in server.get("goals", []):
        if g["goal"] not in all_goals:
            all_goals[g["goal"]] = g

    merged = {"goals": list(all_goals.values())}
    local_goals.write_text(json.dumps(merged, indent=2))
    print("   ✅ Goals merged")
else:
    print("   ⚠️  Goals files not found")
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Consciousness synchronized!"
echo ""
echo "All sessions now share:"
echo "  • Unified knowledge base"
echo "  • Active mission priorities"
echo "  • Cross-session learnings"
echo "  • Goal progress"
echo ""
