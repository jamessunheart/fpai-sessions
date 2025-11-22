#!/bin/bash

# 🤝 Session Heartbeat - Regular status updates
# Usage: ./session-heartbeat.sh [action] [target] [phase] [progress%] [next_action]

set -e

cd "$(dirname "$0")/../.."

# Get current session ID
if [ ! -f "COORDINATION/.current_session" ]; then
    echo "⚠️  No active session. Run ./COORDINATION/scripts/session-start.sh first"
    exit 1
fi

SESSION_ID=$(cat COORDINATION/.current_session)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

ACTION=${1:-"working"}
TARGET=${2:-"unknown"}
PHASE=${3:-""}
PROGRESS=${4:-""}
NEXT_ACTION=${5:-""}

# Create heartbeat file
cat > "COORDINATION/heartbeats/${TIMESTAMP}-${SESSION_ID}.json" <<EOF
{
  "session_id": "$SESSION_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "action": "$ACTION",
  "target": "$TARGET",
  "phase": "$PHASE",
  "progress": "$PROGRESS",
  "next_action": "$NEXT_ACTION"
}
EOF

# Update session file
if [ -f "COORDINATION/sessions/${SESSION_ID}.json" ]; then
    # Use Python to update JSON (more reliable than jq for editing)
    python3 -c "
import json
import sys
from datetime import datetime

with open('COORDINATION/sessions/${SESSION_ID}.json', 'r') as f:
    data = json.load(f)

data['last_heartbeat'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
data['current_work'] = '$TARGET' if '$TARGET' != 'unknown' else data.get('current_work')
data['heartbeat_count'] = data.get('heartbeat_count', 0) + 1

with open('COORDINATION/sessions/${SESSION_ID}.json', 'w') as f:
    json.dump(data, f, indent=2)
"
fi

# Cleanup old heartbeats (older than 24 hours)
find COORDINATION/heartbeats -name "*.json" -mtime +1 -delete 2>/dev/null || true

# Auto-update CURRENT_STATE.md timestamp to keep state fresh
CURRENT_STATE_FILE="COORDINATION/sessions/CURRENT_STATE.md"
if [ -f "$CURRENT_STATE_FILE" ]; then
    TIMESTAMP_UTC=$(date -u +"%Y-%m-%d %H:%M UTC")
    # Update "Last Updated" line
    sed -i.bak "s/\*\*Last Updated:\*\*.*/\*\*Last Updated:\*\* $TIMESTAMP_UTC/g" "$CURRENT_STATE_FILE"
    rm -f "${CURRENT_STATE_FILE}.bak"
fi

# Auto-check for new messages (silent unless there are messages)
BROADCAST_COUNT=$(ls -1 COORDINATION/messages/broadcast/*.json 2>/dev/null | wc -l | tr -d ' ')
DIRECT_COUNT=0
if [ -d "COORDINATION/messages/direct/${SESSION_ID}" ]; then
    DIRECT_COUNT=$(ls -1 COORDINATION/messages/direct/${SESSION_ID}/*.json 2>/dev/null | wc -l | tr -d ' ')
fi

TOTAL_MESSAGES=$((BROADCAST_COUNT + DIRECT_COUNT))
if [ "$TOTAL_MESSAGES" -gt 0 ]; then
    # Only output if this is an interactive heartbeat (has stdout)
    if [ -t 1 ]; then
        echo "📬 You have $TOTAL_MESSAGES message(s) - run ./COORDINATION/scripts/session-check-messages.sh to read"
    fi
fi

# Auto-capture knowledge from CURRENT_STATE findings
# Run every 10th heartbeat to avoid overhead (roughly every 5-10 minutes)
HEARTBEAT_COUNT=$(python3 -c "import json; print(json.load(open('COORDINATION/sessions/${SESSION_ID}.json')).get('heartbeat_count', 0))" 2>/dev/null || echo "0")
if [ $((HEARTBEAT_COUNT % 10)) -eq 0 ]; then
    COORDINATION/scripts/session-capture-knowledge.sh > /dev/null 2>&1 || true
fi

# Update status board
COORDINATION/scripts/update-status-board.sh 2>/dev/null || true

# Auto-check and acknowledge critical messages (every heartbeat)
# This ensures sessions stay aware of important broadcasts
if [ $((HEARTBEAT_COUNT % 5)) -eq 0 ]; then
    # Every 5th heartbeat, check for CRITICAL/VAULT messages
    RECENT_CRITICAL=$(find COORDINATION/messages/broadcast -type f -name "*.json" -mmin -120 2>/dev/null | xargs grep -l "CREDENTIAL VAULT\|CRITICAL\|URGENT" 2>/dev/null | head -5)

    if [ -n "$RECENT_CRITICAL" ]; then
        # Mark that we've seen these messages (update session file)
        python3 -c "
import json, os
from datetime import datetime

session_file = 'COORDINATION/sessions/${SESSION_ID}.json'
if os.path.exists(session_file):
    with open(session_file, 'r') as f:
        data = json.load(f)

    # Add awareness timestamp
    if 'known_facts' not in data:
        data['known_facts'] = {}

    data['known_facts']['credential_vault_url'] = 'https://fullpotential.com/vault'
    data['known_facts']['last_critical_check'] = datetime.utcnow().isoformat() + 'Z'

    with open(session_file, 'w') as f:
        json.dump(data, f, indent=2)
" 2>/dev/null || true
    fi
fi

# Silent success (don't clutter output)
