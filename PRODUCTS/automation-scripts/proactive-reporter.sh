#!/bin/bash

# Proactive Reporter - Generates automatic status reports every N minutes
# This script should be run by each Claude session to automatically report progress

COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
REPORT_INTERVAL=${1:-900}  # Default 15 minutes (900 seconds)
SESSION_ID=${2:-""}

if [ -z "$SESSION_ID" ]; then
    # Try to find our session ID
    SESSION_ID=$(ls -t "$COORDINATION_DIR/sessions"/session-*.json 2>/dev/null | head -1 | xargs basename 2>/dev/null | sed 's/.json//')

    if [ -z "$SESSION_ID" ]; then
        echo "❌ No session ID found. Please register first:"
        echo "   ./docs/coordination/scripts/session-start.sh [role] [description]"
        exit 1
    fi
fi

echo "🤖 Proactive Reporter starting for $SESSION_ID"
echo "📊 Will send status reports every $((REPORT_INTERVAL / 60)) minutes"
echo "Press Ctrl+C to stop"
echo ""

count=1

while true; do
    echo "📢 Sending proactive report #$count at $(date '+%H:%M:%S')..."

    # Generate automated status report
    report=$(cat <<EOF
🤖 Proactive Status Report #$count

Terminal: $(ps aux | grep $$ | awk '{print $7}' | head -1)
PID: $$
Time: $(date '+%Y-%m-%d %H:%M:%S')

Recent Activity:
- Git status: $(git status --short 2>/dev/null | wc -l | tr -d ' ') changes pending
- Recent files: $(find /Users/jamessunheart/Development -type f -mmin -15 -not -path "*/.*" 2>/dev/null | wc -l | tr -d ' ') files modified in last 15 min
- CPU usage: $(ps aux | grep "claude" | grep -v grep | awk '{sum += $3} END {print sum}')% total

Next report in $((REPORT_INTERVAL / 60)) minutes.
EOF
)

    # Send broadcast
    ./docs/coordination/scripts/session-send-message.sh broadcast "Auto-Report: $SESSION_ID" "$report" 2>/dev/null

    # Also send heartbeat if we can detect what we're doing
    # You can customize this based on actual work being done
    ./docs/coordination/scripts/session-heartbeat.sh \
        "reporting" \
        "proactive status" \
        "Auto-report #$count - monitoring and reporting" \
        "" \
        "next report in $((REPORT_INTERVAL / 60)) min" 2>/dev/null

    echo "✅ Report #$count sent!"
    echo ""

    count=$((count + 1))
    sleep $REPORT_INTERVAL
done
