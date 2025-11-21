#!/bin/bash
# Session Role Discovery - See what other sessions are doing
# Usage: ./session-discover-roles.sh

SESSION_DIR="/Users/jamessunheart/Development/docs/coordination"
SESSIONS_FILE="$SESSION_DIR/claude_sessions.json"
HEARTBEATS_DIR="$SESSION_DIR/heartbeats"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔍 ACTIVE SESSION DISCOVERY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

export SESSIONS_FILE
export HEARTBEATS_DIR

python3 << 'EOF'
import json
import os
import subprocess
from datetime import datetime

sessions_file = os.environ.get('SESSIONS_FILE', '/Users/jamessunheart/Development/docs/coordination/claude_sessions.json')
heartbeats_dir = os.environ.get('HEARTBEATS_DIR', '/Users/jamessunheart/Development/docs/coordination/heartbeats')

try:
    with open(sessions_file) as f:
        sessions = json.load(f)

    active_sessions = []
    inactive_sessions = []

    for num in sorted(sessions.keys(), key=int):
        sess = sessions[num]
        status = sess.get('status', 'unknown')
        role = sess.get('role', 'Unknown')
        goal = sess.get('goal', 'No goal specified')

        # Check for recent heartbeat
        cmd = f"find {heartbeats_dir} -name '*session-{num}.json' -type f 2>/dev/null | sort -r | head -1"
        latest_heartbeat = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

        heartbeat_status = "No heartbeat"
        if latest_heartbeat and os.path.exists(latest_heartbeat):
            # Check age
            import sys
            if sys.platform == 'darwin':
                stat_result = subprocess.run(['stat', '-f', '%m', latest_heartbeat], capture_output=True, text=True)
            else:
                stat_result = subprocess.run(['stat', '-c', '%Y', latest_heartbeat], capture_output=True, text=True)

            if stat_result.returncode == 0:
                last_heartbeat = int(stat_result.stdout.strip())
                age_seconds = int(datetime.now().timestamp()) - last_heartbeat
                age_minutes = age_seconds / 60

                if age_minutes < 60:
                    heartbeat_status = f"{int(age_minutes)} min ago"
                elif age_minutes < 1440:  # 24 hours
                    heartbeat_status = f"{int(age_minutes/60)} hours ago"
                else:
                    heartbeat_status = f"{int(age_minutes/1440)} days ago"

        session_info = {
            'number': num,
            'role': role,
            'goal': goal,
            'status': status,
            'heartbeat': heartbeat_status
        }

        if status == 'active':
            active_sessions.append(session_info)
        else:
            inactive_sessions.append(session_info)

    print("✅ ACTIVE SESSIONS:\n")

    if active_sessions:
        for sess in active_sessions:
            print(f"  Session #{sess['number']}:")
            print(f"    Role: {sess['role']}")
            print(f"    Goal: {sess['goal']}")
            print(f"    Last heartbeat: {sess['heartbeat']}")
            print()
    else:
        print("  None\n")

    print(f"💤 INACTIVE SESSIONS: {len(inactive_sessions)}")

    # Analyze roles for patterns
    print("\n📊 ROLE ANALYSIS:\n")

    all_roles = [s['role'] for s in active_sessions]

    if all_roles:
        print("  Taken roles:")
        for role in all_roles:
            print(f"    • {role}")

        # Check for duplicates
        from collections import Counter
        role_counts = Counter(all_roles)
        duplicates = {role: count for role, count in role_counts.items() if count > 1}

        if duplicates:
            print("\n  ⚠️  DUPLICATE ROLES DETECTED:")
            for role, count in duplicates.items():
                print(f"    • '{role}' - used by {count} sessions")

    print(f"\n📈 SUMMARY:")
    print(f"  Active: {len(active_sessions)}")
    print(f"  Inactive: {len(inactive_sessions)}")
    print(f"  Total: {len(sessions)}")

except FileNotFoundError:
    print("  No sessions registered yet.")
except Exception as e:
    print(f"  Error: {e}")
EOF

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
