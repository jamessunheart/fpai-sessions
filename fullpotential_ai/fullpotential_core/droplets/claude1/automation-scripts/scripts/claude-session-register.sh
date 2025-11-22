#!/bin/bash

# Claude Session Registration - Register to SSOT unified registry
# Usage: ./claude-session-register.sh NUMBER "ROLE" "GOAL"

if [ $# -lt 3 ]; then
    echo "Usage: $0 NUMBER \"ROLE\" \"GOAL\" [SESSION_ID] [TERMINAL]"
    echo ""
    echo "Example:"
    echo "  $0 3 \"DevOps Engineer\" \"Deploy and monitor services\" session-3 s003"
    echo ""
    echo "Current registered sessions:"
    cat /Users/jamessunheart/Development/docs/coordination/claude_sessions.json | python3 -m json.tool
    exit 1
fi

NUMBER=$1
ROLE=$2
GOAL=$3
SESSION_ID=${4:-"session-$NUMBER"}
TERMINAL=${5:-"unknown"}
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SESSIONS_FILE="/Users/jamessunheart/Development/docs/coordination/claude_sessions.json"

# Read current sessions
CURRENT=$(cat "$SESSIONS_FILE")

# Check if number already taken
if echo "$CURRENT" | python3 -c "import sys, json; data=json.load(sys.stdin); sys.exit(0 if '$NUMBER' in data else 1)" 2>/dev/null; then
    echo "❌ ERROR: Number $NUMBER is already taken!"
    echo ""
    echo "Taken numbers:"
    cat "$SESSIONS_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f\"  #{k}: {v['role']}\") for k,v in sorted(data.items())]"
    echo ""
    echo "Available numbers: 1-13 (excluding taken numbers above)"
    exit 1
fi

# Add new session
python3 << EOPYTHON
import json

with open("$SESSIONS_FILE", 'r') as f:
    sessions = json.load(f)

sessions["$NUMBER"] = {
    "session_id": "$SESSION_ID",
    "number": int($NUMBER),
    "role": "$ROLE",
    "goal": "$GOAL",
    "status": "active",
    "registered_at": "$TIMESTAMP",
    "terminal": "$TERMINAL"
}

with open("$SESSIONS_FILE", 'w') as f:
    json.dump(sessions, f, indent=2)

print(f"✅ Session #{$NUMBER} registered successfully!")
print(f"   Session ID: $SESSION_ID")
print(f"   Role: $ROLE")
print(f"   Terminal: $TERMINAL")
print("")
print(f"Total sessions registered: {len(sessions)}/13")
EOPYTHON

# Show all sessions
echo ""
echo "All registered sessions:"
cat "$SESSIONS_FILE" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f\"  #{v['number']:2d}. {v['role']:40s} ({v['session_id']})\") for k,v in sorted(data.items(), key=lambda x: int(x[1]['number']))]"
