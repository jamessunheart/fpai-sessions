#!/bin/bash

# Continuous Activity Monitor - Shows real-time feed of ALL activity
# This is like a "tail -f" for all Claude sessions

COORDINATION_DIR="/Users/jamessunheart/Development/docs/coordination"
LAST_CHECK=$(date +%s)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m'

echo -e "${WHITE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${PURPLE}🔴 LIVE ACTIVITY FEED - MONITORING ALL CLAUDE SESSIONS${NC}"
echo -e "${WHITE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GRAY}Started: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${GRAY}Press Ctrl+C to stop${NC}"
echo -e "${WHITE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Track what we've already seen
declare -A seen_heartbeats
declare -A seen_messages
declare -A seen_files

# Initial scan to mark everything as seen
for hb in "$COORDINATION_DIR/heartbeats"/*.json 2>/dev/null; do
    [ -f "$hb" ] && seen_heartbeats["$hb"]=1
done

for msg in "$COORDINATION_DIR/messages/broadcast"/*.json 2>/dev/null; do
    [ -f "$msg" ] && seen_messages["$msg"]=1
done

echo -e "${CYAN}⚡ Monitoring started... waiting for activity...${NC}"
echo ""

while true; do
    has_activity=false

    # Check for new heartbeats
    for hb in "$COORDINATION_DIR/heartbeats"/*.json 2>/dev/null; do
        if [ -f "$hb" ] && [ -z "${seen_heartbeats[$hb]}" ]; then
            seen_heartbeats["$hb"]=1
            has_activity=true

            timestamp=$(date '+%H:%M:%S')
            session=$(jq -r '.session_id // "unknown"' "$hb" 2>/dev/null)
            action=$(jq -r '.action // "..."' "$hb" 2>/dev/null)
            target=$(jq -r '.target // "..."' "$hb" 2>/dev/null)
            phase=$(jq -r '.phase // ""' "$hb" 2>/dev/null)
            progress=$(jq -r '.progress // ""' "$hb" 2>/dev/null)

            echo -e "${GRAY}[${timestamp}]${NC} ${PURPLE}💓 HEARTBEAT${NC} ${session}"
            echo -e "  ${CYAN}→${NC} ${action}: ${WHITE}${target}${NC}"
            if [ -n "$phase" ]; then
                echo -e "  ${GRAY}└─${NC} ${phase} ${progress}"
            fi
            echo ""
        fi
    done

    # Check for new messages
    for msg in "$COORDINATION_DIR/messages/broadcast"/*.json 2>/dev/null; do
        if [ -f "$msg" ] && [ -z "${seen_messages[$msg]}" ]; then
            seen_messages["$msg"]=1
            has_activity=true

            timestamp=$(date '+%H:%M:%S')
            from=$(jq -r '.from // "unknown"' "$msg" 2>/dev/null)
            subject=$(jq -r '.subject // ""' "$msg" 2>/dev/null)
            message=$(jq -r '.message // ""' "$msg" 2>/dev/null)

            echo -e "${GRAY}[${timestamp}]${NC} ${YELLOW}📢 BROADCAST${NC} from ${from}"
            echo -e "  ${WHITE}${subject}${NC}"
            if [ -n "$message" ]; then
                echo -e "  ${GRAY}${message}${NC}"
            fi
            echo ""
        fi
    done

    # Check for new file changes (last 10 seconds)
    new_files=$(find /Users/jamessunheart/Development -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.json" \) -mtime -10s -not -path "*/.*" -not -path "*/venv/*" -not -path "*/node_modules/*" 2>/dev/null)

    for file in $new_files; do
        if [ -f "$file" ] && [ -z "${seen_files[$file]}" ]; then
            seen_files["$file"]=1
            has_activity=true

            timestamp=$(date '+%H:%M:%S')
            rel_path=${file#/Users/jamessunheart/Development/}
            file_type="${file##*.}"

            echo -e "${GRAY}[${timestamp}]${NC} ${GREEN}📝 FILE CHANGE${NC}"
            echo -e "  ${GRAY}└─${NC} ${rel_path}"
            echo ""
        fi
    done

    # Check for new git commits
    for repo_git in $(find /Users/jamessunheart/Development -maxdepth 2 -type d -name ".git" 2>/dev/null); do
        repo_dir=$(dirname "$repo_git")
        repo_name=$(basename "$repo_dir")

        # Check if there's a new commit in last 10 seconds
        new_commit=$(git -C "$repo_dir" log --since="10 seconds ago" --pretty=format:"%H|%s" 2>/dev/null | head -1)

        if [ -n "$new_commit" ] && [ -z "${seen_commits[$new_commit]}" ]; then
            seen_commits["$new_commit"]=1
            has_activity=true

            timestamp=$(date '+%H:%M:%S')
            commit_msg=$(echo "$new_commit" | cut -d'|' -f2)

            echo -e "${GRAY}[${timestamp}]${NC} ${BLUE}📦 GIT COMMIT${NC} in ${WHITE}${repo_name}${NC}"
            echo -e "  ${GRAY}└─${NC} ${commit_msg}"
            echo ""
        fi
    done

    # Visual separator if there was activity
    if [ "$has_activity" = true ]; then
        echo -e "${GRAY}───────────────────────────────────────────────────────────────${NC}"
        echo ""
    fi

    sleep 3
done
