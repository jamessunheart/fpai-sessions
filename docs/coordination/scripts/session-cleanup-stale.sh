#!/bin/bash

# 🧹 Session Cleanup - Mark stale sessions as inactive
# Usage: ./session-cleanup-stale.sh [--timeout-minutes MINUTES] [--dry-run]
#
# This script checks for sessions that haven't sent a heartbeat recently
# and marks them as inactive in the registry.

set -e

TIMEOUT_MINUTES=120  # Default: 2 hours
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout-minutes)
            TIMEOUT_MINUTES="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--timeout-minutes MINUTES] [--dry-run]"
            exit 1
            ;;
    esac
done

SESSIONS_FILE="/Users/jamessunheart/Development/docs/coordination/claude_sessions.json"
HEARTBEATS_DIR="/Users/jamessunheart/Development/docs/coordination/heartbeats"

echo "🧹 Session Cleanup Tool"
echo "======================="
echo ""
echo "Configuration:"
echo "  Timeout: ${TIMEOUT_MINUTES} minutes"
echo "  Dry Run: ${DRY_RUN}"
echo ""

# Get current time in epoch seconds
NOW=$(date +%s)
TIMEOUT_SECONDS=$((TIMEOUT_MINUTES * 60))

# Function to get last heartbeat timestamp for a session
get_last_heartbeat() {
    local session_id=$1
    local latest_heartbeat=$(find "$HEARTBEATS_DIR" -name "*-${session_id}.json" -type f 2>/dev/null | sort -r | head -1)

    if [ -z "$latest_heartbeat" ]; then
        echo "never"
        return
    fi

    # Get file modification time in epoch seconds
    if [[ "$OSTYPE" == "darwin"* ]]; then
        stat -f %m "$latest_heartbeat"
    else
        stat -c %Y "$latest_heartbeat"
    fi
}

# Export for Python
export SESSIONS_FILE
export HEARTBEATS_DIR
export TIMEOUT_SECONDS
export NOW
export DRY_RUN

# Read sessions and check heartbeats
python3 << 'EOPYTHON'
import json
import sys
import os
import subprocess
from datetime import datetime, timedelta

sessions_file = os.environ['SESSIONS_FILE']
heartbeats_dir = os.environ['HEARTBEATS_DIR']
timeout_seconds = int(os.environ['TIMEOUT_SECONDS'])
now = int(os.environ['NOW'])
dry_run = os.environ['DRY_RUN'] == 'true'

with open(sessions_file, 'r') as f:
    sessions = json.load(f)

stale_sessions = []
active_sessions = []

print("Checking sessions:")
print("")

for number, session in sorted(sessions.items(), key=lambda x: int(x[0])):
    session_id = session.get('session_id', f"session-{number}")
    current_status = session.get('status', 'unknown')

    # Find latest heartbeat file for this session
    cmd = f"find {heartbeats_dir} -name '*-{session_id}.json' -type f 2>/dev/null | sort -r | head -1"
    latest_heartbeat = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

    if not latest_heartbeat:
        time_since_str = "Never"
        is_stale = True
        age_minutes = float('inf')
    else:
        # Get file modification time
        if sys.platform == 'darwin':
            stat_result = subprocess.run(['stat', '-f', '%m', latest_heartbeat], capture_output=True, text=True)
        else:
            stat_result = subprocess.run(['stat', '-c', '%Y', latest_heartbeat], capture_output=True, text=True)

        last_heartbeat = int(stat_result.stdout.strip())
        age_seconds = now - last_heartbeat
        age_minutes = age_seconds / 60

        hours = int(age_minutes // 60)
        minutes = int(age_minutes % 60)
        time_since_str = f"{hours}h {minutes}m ago"

        is_stale = age_seconds > timeout_seconds

    status_emoji = "💤" if is_stale else "✅"
    print(f"  {status_emoji} Session #{int(number):2d} ({session_id})")
    print(f"     Last heartbeat: {time_since_str}")
    print(f"     Current status: {current_status}")

    if is_stale and current_status == "active":
        stale_sessions.append((number, session_id, time_since_str))
        print(f"     → Will mark as INACTIVE (timeout exceeded)")
    elif not is_stale and current_status == "active":
        active_sessions.append((number, session_id))
        print(f"     → Staying ACTIVE")

    print("")

print("")
print("Summary:")
print(f"  ✅ Active sessions: {len(active_sessions)}")
print(f"  💤 Stale sessions: {len(stale_sessions)}")
print("")

if len(stale_sessions) > 0:
    print("Stale sessions to update:")
    for number, session_id, time_since in stale_sessions:
        print(f"  #{number} ({session_id}) - Last seen: {time_since}")
    print("")

    if not dry_run:
        print("Updating session registry...")
        for number, session_id, _ in stale_sessions:
            sessions[str(number)]['status'] = 'inactive'
            sessions[str(number)]['marked_inactive_at'] = datetime.utcnow().isoformat() + 'Z'

        with open(sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)

        print(f"✅ Marked {len(stale_sessions)} session(s) as inactive")
    else:
        print("🔍 DRY RUN - No changes made")
else:
    print("✨ All active sessions are healthy!")

EOPYTHON

echo ""
echo "Done!"
