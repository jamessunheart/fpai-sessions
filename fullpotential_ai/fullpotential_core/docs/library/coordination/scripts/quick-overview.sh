#!/bin/bash

# Quick Overview - One-screen summary of everything

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m'

COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
SERVER="198.54.123.234"

clear

echo -e "${WHITE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${WHITE}║${NC}  ${PURPLE}⚡ QUICK SYSTEM OVERVIEW${NC}                                          ${WHITE}║${NC}"
echo -e "${WHITE}║${NC}  ${GRAY}$(date '+%Y-%m-%d %H:%M:%S')${NC}                                              ${WHITE}║${NC}"
echo -e "${WHITE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Claude processes
claude_count=$(ps aux | grep -E "^\S+\s+\d+.*claude$" | grep -v grep | wc -l | tr -d ' ')
registered_count=$(ls -1 "$COORDINATION_DIR/sessions"/*.json 2>/dev/null | wc -l | tr -d ' ')

echo -e "${CYAN}🤖 Claude Code Instances:${NC} $claude_count running | $registered_count registered"
echo ""

# Registered sessions with latest status
if [ "$registered_count" -gt 0 ]; then
    for session_file in "$COORDINATION_DIR/sessions"/session-*.json; do
        session_id=$(basename "$session_file" .json)
        current_work=$(jq -r '.current_work // "idle"' "$session_file" 2>/dev/null)

        # Get latest heartbeat
        latest_hb=$(ls -t "$COORDINATION_DIR/heartbeats"/*-${session_id}.json 2>/dev/null | head -1)
        if [ -f "$latest_hb" ]; then
            action=$(jq -r '.action // "waiting"' "$latest_hb" 2>/dev/null)
            phase=$(jq -r '.phase // ""' "$latest_hb" 2>/dev/null)
            hb_time=$(basename "$latest_hb" | cut -d'-' -f1-2 | sed 's/_/ /')

            # Truncate phase if too long
            phase_short=$(echo "$phase" | cut -c1-50)

            echo -e "  ${GREEN}●${NC} ${session_id}: ${YELLOW}${action}${NC} - ${phase_short}"
            echo -e "    ${GRAY}Last seen: ${hb_time}${NC}"
        else
            echo -e "  ${GRAY}○${NC} ${session_id}: ${current_work}"
        fi
    done
fi

echo ""
echo -e "${CYAN}🌐 Server Services:${NC}"

# Quick server check
services=("8000:Registry" "8001:Orchestrator" "8002:Dashboard" "8009:Church" "8010:I-Match")

for service in "${services[@]}"; do
    port=${service%%:*}
    name=${service##*:}

    response=$(curl -s --connect-timeout 1 "http://$SERVER:$port/health" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo -e "  ${GREEN}●${NC} $name (Port $port)"
    else
        echo -e "  ${RED}○${NC} $name (Port $port) - offline"
    fi
done

echo ""
echo -e "${CYAN}💬 Latest Message:${NC}"

# Show most recent broadcast
latest_msg=$(ls -t "$COORDINATION_DIR/messages/broadcast"/*.json 2>/dev/null | head -1)
if [ -f "$latest_msg" ]; then
    from=$(jq -r '.from // "unknown"' "$latest_msg" 2>/dev/null)
    subject=$(jq -r '.subject // ""' "$latest_msg" 2>/dev/null)
    timestamp=$(jq -r '.timestamp // ""' "$latest_msg" 2>/dev/null | cut -d'T' -f2 | cut -d'.' -f1)

    echo -e "  ${GRAY}[${timestamp}]${NC} ${from}: ${WHITE}${subject}${NC}"
else
    echo -e "  ${GRAY}No messages${NC}"
fi

echo ""
echo -e "${CYAN}📝 Recent Changes (last 5 min):${NC}"

# Recent file changes
changes=$(find /Users/jamessunheart/Development -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" \) -mmin -5 -not -path "*/.*" -not -path "*/venv/*" 2>/dev/null | head -5)

if [ -n "$changes" ]; then
    echo "$changes" | while read -r file; do
        rel_path=${file#/Users/jamessunheart/Development/}
        mod_time=$(stat -f "%Sm" -t "%H:%M:%S" "$file" 2>/dev/null)
        echo -e "  ${GREEN}●${NC} ${GRAY}[${mod_time}]${NC} ${rel_path}"
    done
else
    echo -e "  ${GRAY}No recent changes${NC}"
fi

echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Commands:${NC}"
echo -e "  ${WHITE}./docs/coordination/scripts/live-monitor.sh${NC}          - Live dashboard"
echo -e "  ${WHITE}./docs/coordination/scripts/detailed-process-monitor.sh${NC} - Process details"
echo -e "  ${WHITE}./docs/coordination/scripts/session-status.sh${NC}       - Session status"
echo ""
