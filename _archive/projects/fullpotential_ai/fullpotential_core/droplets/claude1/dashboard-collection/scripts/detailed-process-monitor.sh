#!/bin/bash

# Detailed Process Monitor - Shows what each Claude terminal is doing
# Maps PIDs to actual work being performed

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

echo -e "${WHITE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${WHITE}║${NC}  ${PURPLE}🔍 DETAILED CLAUDE CODE PROCESS MONITOR${NC}                    ${WHITE}║${NC}"
echo -e "${WHITE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get all Claude processes
claude_processes=$(ps aux | grep -E "^\S+\s+\d+.*claude$" | grep -v grep)

if [ -z "$claude_processes" ]; then
    echo -e "${YELLOW}No Claude Code processes found.${NC}"
    exit 0
fi

echo -e "${CYAN}Active Claude Code Processes:${NC}"
echo ""

# Counter
count=1

echo "$claude_processes" | while read -r line; do
    pid=$(echo "$line" | awk '{print $2}')
    cpu=$(echo "$line" | awk '{print $3}')
    mem=$(echo "$line" | awk '{print $4}')
    time=$(echo "$line" | awk '{print $10}')
    tty=$(echo "$line" | awk '{print $7}')

    # Get working directory for this process
    cwd=$(lsof -p "$pid" 2>/dev/null | grep cwd | awk '{print $NF}')

    # Get last command in this terminal session
    last_cmd=""
    if [[ "$tty" =~ ^s[0-9]+ ]]; then
        # Try to get the last command from the terminal
        last_cmd=$(lsof -p "$pid" 2>/dev/null | grep -E "\.(py|sh|js|json)$" | head -1 | awk '{print $NF}')
    fi

    # Status indicator based on CPU usage
    if (( $(echo "$cpu > 50" | bc -l) )); then
        status="🔴 HIGH CPU"
    elif (( $(echo "$cpu > 10" | bc -l) )); then
        status="🟡 ACTIVE"
    else
        status="🟢 IDLE"
    fi

    echo -e "${WHITE}Process #$count${NC} ${status}"
    echo -e "   ${GRAY}├─${NC} PID: ${CYAN}$pid${NC} | Terminal: ${CYAN}$tty${NC}"
    echo -e "   ${GRAY}├─${NC} CPU: ${YELLOW}${cpu}%${NC} | Memory: ${YELLOW}${mem}%${NC} | Time: ${GRAY}${time}${NC}"

    if [ -n "$cwd" ]; then
        # Make path relative to Development
        rel_cwd=${cwd#/Users/jamessunheart/Development/}
        if [ "$rel_cwd" = "$cwd" ]; then
            echo -e "   ${GRAY}├─${NC} Working Dir: ${cwd}"
        else
            echo -e "   ${GRAY}├─${NC} Working Dir: ${GREEN}~Development/${rel_cwd}${NC}"
        fi
    fi

    if [ -n "$last_cmd" ]; then
        echo -e "   ${GRAY}└─${NC} Last File: ${PURPLE}$(basename "$last_cmd")${NC}"
    else
        echo -e "   ${GRAY}└─${NC} Activity: ${GRAY}(monitoring...)${NC}"
    fi

    echo ""
    count=$((count + 1))
done

echo ""
echo -e "${CYAN}Total Processes:${NC} $(echo "$claude_processes" | wc -l | tr -d ' ')"
echo ""

# Show which terminals have active git operations
echo -e "${CYAN}Recent Terminal Activity:${NC}"
echo ""

# Check for recent bash history in active terminals
for tty_session in s001 s002 s003 s004 s005 s006 s007 s008 s009; do
    pid=$(ps aux | grep "claude$" | grep "$tty_session" | grep -v grep | awk '{print $2}' | head -1)

    if [ -n "$pid" ]; then
        # Try to infer what this terminal is working on
        cwd=$(lsof -p "$pid" 2>/dev/null | grep cwd | awk '{print $NF}')

        if [ -n "$cwd" ]; then
            # Check if there's a git repo
            if [ -d "$cwd/.git" ]; then
                repo_name=$(basename "$cwd")
                branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
                status=$(git -C "$cwd" status --short 2>/dev/null | wc -l | tr -d ' ')

                if [ "$status" -gt 0 ]; then
                    echo -e "${GREEN}●${NC} ${tty_session}: ${WHITE}${repo_name}${NC} (${CYAN}${branch}${NC}) - ${YELLOW}${status} changes${NC}"
                else
                    echo -e "${GRAY}○${NC} ${tty_session}: ${WHITE}${repo_name}${NC} (${CYAN}${branch}${NC}) - clean"
                fi
            else
                rel_cwd=${cwd#/Users/jamessunheart/Development/}
                echo -e "${BLUE}●${NC} ${tty_session}: ${rel_cwd}"
            fi
        fi
    fi
done

echo ""
