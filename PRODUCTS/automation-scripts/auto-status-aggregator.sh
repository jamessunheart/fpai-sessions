#!/bin/bash

# Auto Status Aggregator - Collects status from all sessions and generates summary
# Run this to get a comprehensive report of all 13 sessions

COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
OUTPUT_FILE="/Users/jamessunheart/Development/docs/coordination/LIVE_STATUS_REPORT.md"

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${WHITE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}📊 GENERATING COMPREHENSIVE STATUS REPORT FOR ALL SESSIONS${NC}"
echo -e "${WHITE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Start report
cat > "$OUTPUT_FILE" << 'HEADER'
# 📊 LIVE SYSTEM STATUS REPORT

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Auto-Generated:** Every 5 minutes
**Total Sessions:** 13 Claude Code instances

---

## 🚦 EXECUTIVE SUMMARY

HEADER

# Add timestamp
echo "**Generated:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Count sessions
total_sessions=$(ps aux | grep -E "^\S+\s+\d+.*claude$" | grep -v grep | wc -l | tr -d ' ')
registered=$(ls -1 "$COORDINATION_DIR/sessions"/*.json 2>/dev/null | wc -l | tr -d ' ')
unregistered=$((total_sessions - registered))

echo "**Total Claude Instances:** $total_sessions" >> "$OUTPUT_FILE"
echo "**Registered Sessions:** $registered" >> "$OUTPUT_FILE"
echo "**Unregistered Sessions:** $unregistered ⚠️" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Git status
git_changes=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
echo "**Pending Git Changes:** $git_changes" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Server status
echo "**Server Status (198.54.123.234):**" >> "$OUTPUT_FILE"
for port in 8000 8001 8002 8009 8010 8025; do
    response=$(curl -s --connect-timeout 1 "http://198.54.123.234:$port/health" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "- ✅ Port $port - Online" >> "$OUTPUT_FILE"
    else
        echo "- ❌ Port $port - Offline" >> "$OUTPUT_FILE"
    fi
done

echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Process details
echo "## 🤖 ALL ACTIVE CLAUDE SESSIONS" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "| Terminal | PID | CPU | Memory | Status | Time Active |" >> "$OUTPUT_FILE"
echo "|----------|-----|-----|--------|--------|-------------|" >> "$OUTPUT_FILE"

ps aux | grep -E "^\S+\s+\d+.*claude$" | grep -v grep | while read -r line; do
    pid=$(echo "$line" | awk '{print $2}')
    cpu=$(echo "$line" | awk '{print $3}')
    mem=$(echo "$line" | awk '{print $4}')
    time=$(echo "$line" | awk '{print $10}')
    tty=$(echo "$line" | awk '{print $7}')

    # Status based on CPU
    if (( $(echo "$cpu > 50" | bc -l 2>/dev/null || echo 0) )); then
        status="🔴 HIGH CPU"
    elif (( $(echo "$cpu > 10" | bc -l 2>/dev/null || echo 0) )); then
        status="🟡 ACTIVE"
    else
        status="🟢 IDLE"
    fi

    echo "| $tty | $pid | ${cpu}% | ${mem}% | $status | $time |" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Registered sessions with latest activity
echo "## 📋 REGISTERED SESSIONS (Coordination System)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

if [ "$registered" -eq 0 ]; then
    echo "⚠️ **No sessions registered yet!**" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "**Action Required:** All sessions should run:" >> "$OUTPUT_FILE"
    echo '```bash' >> "$OUTPUT_FILE"
    echo './docs/coordination/scripts/session-start.sh [role] [description]' >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
else
    for session_file in "$COORDINATION_DIR/sessions"/session-*.json; do
        if [ -f "$session_file" ]; then
            session_id=$(basename "$session_file" .json)
            status=$(jq -r '.status // "unknown"' "$session_file" 2>/dev/null)
            work=$(jq -r '.current_work // "unknown"' "$session_file" 2>/dev/null)
            started=$(jq -r '.started // ""' "$session_file" 2>/dev/null)

            echo "### $session_id" >> "$OUTPUT_FILE"
            echo "- **Status:** $status" >> "$OUTPUT_FILE"
            echo "- **Current Work:** $work" >> "$OUTPUT_FILE"
            echo "- **Started:** $started" >> "$OUTPUT_FILE"

            # Get latest heartbeat
            latest_hb=$(ls -t "$COORDINATION_DIR/heartbeats"/*-${session_id}.json 2>/dev/null | head -1)
            if [ -f "$latest_hb" ]; then
                action=$(jq -r '.action // ""' "$latest_hb" 2>/dev/null)
                target=$(jq -r '.target // ""' "$latest_hb" 2>/dev/null)
                phase=$(jq -r '.phase // ""' "$latest_hb" 2>/dev/null)

                echo "- **Latest Action:** $action - $target" >> "$OUTPUT_FILE"
                echo "- **Phase:** $phase" >> "$OUTPUT_FILE"
            fi

            echo "" >> "$OUTPUT_FILE"
        fi
    done
fi

echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Recent messages
echo "## 💬 RECENT MESSAGES (Last 10)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

msg_count=0
for msg_file in $(ls -t "$COORDINATION_DIR/messages/broadcast"/*.json 2>/dev/null | head -10); do
    if [ -f "$msg_file" ]; then
        from=$(jq -r '.from // "unknown"' "$msg_file" 2>/dev/null)
        subject=$(jq -r '.subject // ""' "$msg_file" 2>/dev/null)
        timestamp=$(jq -r '.timestamp // ""' "$msg_file" 2>/dev/null)

        echo "**[$timestamp]** $from: **$subject**" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        msg_count=$((msg_count + 1))
    fi
done

if [ $msg_count -eq 0 ]; then
    echo "No messages found." >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Recent file changes
echo "## 📝 RECENT FILE CHANGES (Last 15 min)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

changes=$(find /Users/jamessunheart/Development -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.json" \) -mmin -15 -not -path "*/.*" -not -path "*/venv/*" 2>/dev/null | head -20)

if [ -n "$changes" ]; then
    echo "$changes" | while read -r file; do
        rel_path=${file#/Users/jamessunheart/Development/}
        mod_time=$(stat -f "%Sm" -t "%H:%M:%S" "$file" 2>/dev/null)
        echo "- **[$mod_time]** $rel_path" >> "$OUTPUT_FILE"
    done
else
    echo "No recent file changes." >> "$OUTPUT_FILE"
fi

echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Footer
echo "**Next Update:** In 5 minutes" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "**Commands:**" >> "$OUTPUT_FILE"
echo '- Live monitor: `./docs/coordination/scripts/live-monitor.sh`' >> "$OUTPUT_FILE"
echo '- Session status: `./docs/coordination/scripts/session-status.sh`' >> "$OUTPUT_FILE"
echo '- This report: `cat docs/coordination/LIVE_STATUS_REPORT.md`' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo -e "${GREEN}✅ Report generated: $OUTPUT_FILE${NC}"
echo -e "${CYAN}📄 View with: cat $OUTPUT_FILE${NC}"
echo ""

# Also output to terminal
cat "$OUTPUT_FILE"
