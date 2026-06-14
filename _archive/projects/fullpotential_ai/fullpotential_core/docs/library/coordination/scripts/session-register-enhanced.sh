#!/bin/bash
# Enhanced Session Registration with Collision Detection
# Prevents duplicate session numbers through fingerprint validation
# Usage: ./session-register-enhanced.sh <number> "<role>" "<goal>"

set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: $0 <number> '<role>' '<goal>'"
    echo "Example: $0 1 'Forge - Infrastructure Builder' 'Build core services'"
    exit 1
fi

SESSION_NUMBER="$1"
ROLE="$2"
GOAL="$3"

COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
SESSIONS_FILE="$COORDINATION_DIR/claude_sessions.json"
HEARTBEATS_DIR="$COORDINATION_DIR/heartbeats"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Generate fingerprint
CURRENT_PID=$$
PARENT_PID=$PPID
TERMINAL=$(tty 2>/dev/null || echo "not a tty")
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ "$OSTYPE" == "darwin"* ]]; then
    PARENT_NAME=$(ps -p $PARENT_PID -o comm= 2>/dev/null || echo "unknown")
else
    PARENT_NAME=$(ps -p $PARENT_PID -o comm= 2>/dev/null || echo "unknown")
fi

FINGERPRINT="${CURRENT_PID}_$(date +%s)"

echo -e "${BLUE}🔐 ENHANCED SESSION REGISTRATION${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Session Number:${NC} $SESSION_NUMBER"
echo -e "${CYAN}Role:${NC}           $ROLE"
echo -e "${CYAN}Goal:${NC}           $GOAL"
echo -e "${CYAN}PID:${NC}            $CURRENT_PID"
echo -e "${CYAN}Terminal:${NC}       $TERMINAL"
echo -e "${CYAN}Fingerprint:${NC}    $FINGERPRINT"
echo ""

# Check for existing active sessions with same number
COLLISION_CHECK=$(python3 << EOF
import json
import sys
from pathlib import Path
from datetime import datetime

sessions_file = Path("$SESSIONS_FILE")
heartbeats_dir = Path("$HEARTBEATS_DIR")

# Load existing sessions
try:
    with open(sessions_file) as f:
        sessions = json.load(f)
except FileNotFoundError:
    sessions = {}

# Check if this number is already taken by an ACTIVE session
if "$SESSION_NUMBER" in sessions:
    existing = sessions["$SESSION_NUMBER"]

    # Check if session is active
    if existing.get('status') == 'active':
        # Check for recent heartbeat
        heartbeat_files = sorted(heartbeats_dir.glob(f"*session-$SESSION_NUMBER.json"))

        if heartbeat_files:
            latest = heartbeat_files[-1]
            try:
                # Check age of heartbeat
                import os
                if sys.platform == 'darwin':
                    import subprocess
                    result = subprocess.run(['stat', '-f', '%m', str(latest)],
                                          capture_output=True, text=True)
                    mtime = int(result.stdout.strip())
                else:
                    mtime = int(os.path.getmtime(latest))

                age_seconds = int(datetime.now().timestamp()) - mtime

                # If heartbeat < 30 min old, there's a collision
                if age_seconds < 1800:
                    print(f"COLLISION|{existing.get('role', 'Unknown')}|{age_seconds}|{existing.get('terminal', 'unknown')}")
                    sys.exit(0)
            except:
                pass

        # Also check if PID is still running
        existing_pid = existing.get('fingerprint', {}).get('pid')
        if existing_pid:
            try:
                import os
                os.kill(int(existing_pid), 0)  # Check if process exists
                print(f"PID_COLLISION|{existing.get('role', 'Unknown')}|{existing_pid}|{existing.get('terminal', 'unknown')}")
                sys.exit(0)
            except:
                pass  # PID not running, can proceed

print("OK")
EOF
)

if [[ $COLLISION_CHECK == COLLISION* ]]; then
    IFS='|' read -r status role age terminal <<< "$COLLISION_CHECK"
    AGE_MIN=$((age / 60))

    echo -e "${RED}❌ COLLISION DETECTED${NC}"
    echo ""
    echo "Session #$SESSION_NUMBER is already ACTIVE:"
    echo "  Role: $role"
    echo "  Terminal: $terminal"
    echo "  Last heartbeat: ${AGE_MIN}m ago"
    echo ""
    echo -e "${YELLOW}This likely means:${NC}"
    echo "  1. You have another Claude session open"
    echo "  2. A previous session didn't clean up properly"
    echo ""
    echo "Options:"
    echo "  - Choose a different session number"
    echo "  - Check running sessions: ./session-discover-roles.sh"
    echo "  - Clean up stale sessions: ./session-cleanup-stale.sh"
    exit 1
fi

if [[ $COLLISION_CHECK == PID_COLLISION* ]]; then
    IFS='|' read -r status role pid terminal <<< "$COLLISION_CHECK"

    echo -e "${RED}❌ PROCESS COLLISION DETECTED${NC}"
    echo ""
    echo "Session #$SESSION_NUMBER has an active process:"
    echo "  Role: $role"
    echo "  PID: $pid"
    echo "  Terminal: $terminal"
    echo ""
    echo "The process is still running. Please choose a different number."
    exit 1
fi

# Register session
python3 << EOF
import json
from pathlib import Path
from datetime import datetime

sessions_file = Path("$SESSIONS_FILE")

# Load existing sessions
try:
    with open(sessions_file) as f:
        sessions = json.load(f)
except FileNotFoundError:
    sessions = {}

# Create session entry
session_id = f"session-{$SESSION_NUMBER}"

sessions["$SESSION_NUMBER"] = {
    "session_id": session_id,
    "number": $SESSION_NUMBER,
    "role": "$ROLE",
    "goal": "$GOAL",
    "status": "active",
    "registered_at": "$START_TIME",
    "terminal": "$TERMINAL",
    "fingerprint": {
        "pid": $CURRENT_PID,
        "ppid": $PARENT_PID,
        "parent_name": "$PARENT_NAME",
        "terminal": "$TERMINAL",
        "start_time": "$START_TIME",
        "fingerprint": "$FINGERPRINT"
    }
}

# Save
sessions_file.parent.mkdir(parents=True, exist_ok=True)
with open(sessions_file, 'w') as f:
    json.dump(sessions, f, indent=2)

# Save session ID to .current_session
with open(sessions_file.parent / '.current_session', 'w') as f:
    f.write(session_id)

print(f"✅ Session #{$SESSION_NUMBER} registered successfully")
print(f"   Session ID: {session_id}")
print(f"   Fingerprint: $FINGERPRINT")
EOF

# Create initial heartbeat
mkdir -p "$HEARTBEATS_DIR"
python3 << EOF
import json
from datetime import datetime
from pathlib import Path

heartbeat = {
    "session_number": $SESSION_NUMBER,
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "status": "active",
    "pid": $CURRENT_PID,
    "terminal": "$TERMINAL",
    "role": "$ROLE"
}

heartbeat_file = Path("$HEARTBEATS_DIR") / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}-session-{$SESSION_NUMBER}.json"
with open(heartbeat_file, 'w') as f:
    json.dump(heartbeat, f, indent=2)
EOF

echo ""
echo -e "${GREEN}✅ REGISTRATION COMPLETE${NC}"
echo ""
echo "Your session identity:"
echo "  Number: #$SESSION_NUMBER"
echo "  Role: $ROLE"
echo "  PID: $CURRENT_PID"
echo "  Terminal: $TERMINAL"
echo ""
echo "Next steps:"
echo "  - View all sessions: ./session-discover-roles.sh"
echo "  - Send heartbeat: ./session-heartbeat.sh"
echo "  - Claim tasks: ./task-claim.sh <id> '<description>'"
echo ""
