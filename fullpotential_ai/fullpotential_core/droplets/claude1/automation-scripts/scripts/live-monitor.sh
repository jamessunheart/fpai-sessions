#!/bin/bash

# Live Activity Monitor for Claude Code Sessions + Server + Development
# Shows real-time activity across all systems

COORDINATION_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION_DIR="$COORDINATION_DIR/sessions"
HEARTBEAT_DIR="$COORDINATION_DIR/heartbeats"
MESSAGE_DIR="$COORDINATION_DIR/messages"
DEV_DIR="/Users/jamessunheart/Development"
SERVER="198.54.123.234"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Get terminal size
COLS=$(tput cols)
LINES=$(tput lines)

# Helper functions
hr() {
    printf "${GRAY}%${COLS}s${NC}\n" | tr ' ' '─'
}

header() {
    echo -e "${WHITE}$1${NC}"
}

subheader() {
    echo -e "${CYAN}$1${NC}"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to get Claude sessions
get_claude_sessions() {
    local sessions=$(ps aux | grep -i "claude" | grep -v grep | grep -v "Claude.app" | grep -v "Helper" | grep -v "Squirrel" | grep -v "zsh -c")
    echo "$sessions"
}

# Function to count active sessions
count_sessions() {
    local count=$(get_claude_sessions | wc -l | tr -d ' ')
    echo "$count"
}

# Function to get server health
check_server_health() {
    local port=$1
    local response=$(curl -s --connect-timeout 2 "http://$SERVER:$port/health" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "🟢"
    else
        echo "🔴"
    fi
}

# Function to get recent file changes
get_recent_changes() {
    find "$DEV_DIR" -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.json" \) -mmin -5 -not -path "*/.*" -not -path "*/venv/*" -not -path "*/node_modules/*" 2>/dev/null | head -10
}

# Function to get recent git activity
get_git_activity() {
    local repos=$(find "$DEV_DIR" -maxdepth 2 -type d -name ".git" 2>/dev/null)
    for repo_git in $repos; do
        local repo_dir=$(dirname "$repo_git")
        local repo_name=$(basename "$repo_dir")
        local last_commit=$(git -C "$repo_dir" log -1 --pretty=format:"%ar|%s" 2>/dev/null)
        if [ -n "$last_commit" ]; then
            echo "$repo_name|$last_commit"
        fi
    done
}

# Function to display everything
display_dashboard() {
    clear

    # Header
    echo -e "${WHITE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║${NC}  ${PURPLE}🤖 LIVE CLAUDE CODE & SYSTEM ACTIVITY MONITOR${NC}                    ${WHITE}║${NC}"
    echo -e "${WHITE}║${NC}  ${GRAY}Updated: $(date '+%Y-%m-%d %H:%M:%S')${NC}                                    ${WHITE}║${NC}"
    echo -e "${WHITE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # ==================== SECTION 1: CLAUDE SESSIONS ====================
    header "━━━ 🤖 ACTIVE CLAUDE CODE SESSIONS ━━━"
    echo ""

    local session_count=$(count_sessions)
    local registered_count=$(ls -1 "$SESSION_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')

    echo -e "${CYAN}Process Count:${NC} $session_count running | ${CYAN}Registered:${NC} $registered_count sessions"
    echo ""

    # Show registered sessions with their latest heartbeat
    if [ -d "$SESSION_DIR" ]; then
        for session_file in "$SESSION_DIR"/session-*.json; do
            if [ -f "$session_file" ]; then
                local session_id=$(basename "$session_file" .json)
                local status=$(jq -r '.status // "unknown"' "$session_file" 2>/dev/null)
                local current_work=$(jq -r '.current_work // "idle"' "$session_file" 2>/dev/null)
                local started=$(jq -r '.started // ""' "$session_file" 2>/dev/null)

                # Get latest heartbeat
                local latest_hb=$(ls -t "$HEARTBEAT_DIR"/*-${session_id}.json 2>/dev/null | head -1)
                local hb_action="waiting"
                local hb_phase="..."
                local hb_progress=""
                local hb_time="unknown"

                if [ -f "$latest_hb" ]; then
                    hb_action=$(jq -r '.action // "waiting"' "$latest_hb" 2>/dev/null)
                    hb_phase=$(jq -r '.phase // "..."' "$latest_hb" 2>/dev/null)
                    hb_progress=$(jq -r '.progress // ""' "$latest_hb" 2>/dev/null)
                    hb_time=$(basename "$latest_hb" | cut -d'-' -f1-2 | sed 's/_/ /')
                fi

                # Status indicator
                local status_icon="🟡"
                case "$hb_action" in
                    "completed") status_icon="🟢" ;;
                    "building"|"deploying"|"testing") status_icon="🔵" ;;
                    "error"|"failed") status_icon="🔴" ;;
                esac

                echo -e "${status_icon} ${WHITE}${session_id}${NC}"
                echo -e "   ${GRAY}├─${NC} Status: ${CYAN}${status}${NC} | Action: ${YELLOW}${hb_action}${NC}"
                echo -e "   ${GRAY}├─${NC} Working on: ${GREEN}${current_work}${NC}"
                echo -e "   ${GRAY}├─${NC} Phase: ${hb_phase} ${hb_progress}"
                echo -e "   ${GRAY}└─${NC} Last seen: ${GRAY}${hb_time}${NC}"
                echo ""
            fi
        done
    else
        warning "No registered sessions found"
        echo ""
    fi

    hr

    # ==================== SECTION 2: RECENT MESSAGES ====================
    header "━━━ 💬 RECENT SESSION MESSAGES ━━━"
    echo ""

    # Show last 5 broadcast messages
    if [ -d "$MESSAGE_DIR/broadcast" ]; then
        local msg_count=0
        for msg_file in $(ls -t "$MESSAGE_DIR/broadcast"/*.json 2>/dev/null | head -5); do
            if [ -f "$msg_file" ]; then
                local from=$(jq -r '.from // "unknown"' "$msg_file" 2>/dev/null)
                local subject=$(jq -r '.subject // ""' "$msg_file" 2>/dev/null)
                local message=$(jq -r '.message // ""' "$msg_file" 2>/dev/null)
                local timestamp=$(jq -r '.timestamp // ""' "$msg_file" 2>/dev/null | cut -d'T' -f2 | cut -d'.' -f1)

                echo -e "${PURPLE}📢${NC} ${GRAY}[${timestamp}]${NC} ${CYAN}${from}${NC}: ${WHITE}${subject}${NC}"
                echo -e "   ${GRAY}${message}${NC}"
                echo ""
                msg_count=$((msg_count + 1))
            fi
        done

        if [ $msg_count -eq 0 ]; then
            info "No recent messages"
            echo ""
        fi
    fi

    hr

    # ==================== SECTION 3: SERVER HEALTH ====================
    header "━━━ 🌐 SERVER SERVICES (198.54.123.234) ━━━"
    echo ""

    # Check key services
    declare -A services=(
        ["8000"]="Registry"
        ["8001"]="Orchestrator"
        ["8002"]="Dashboard"
        ["8009"]="Church Guidance"
        ["8010"]="I-Match"
        ["8020"]="White Rock Ministry"
        ["8025"]="Credentials Manager"
    )

    echo -e "${CYAN}Service Status:${NC}"
    for port in "${!services[@]}"; do
        local name="${services[$port]}"
        local health=$(check_server_health "$port")
        printf "   %-25s %s\n" "$name (Port $port):" "$health"
    done
    echo ""

    hr

    # ==================== SECTION 4: RECENT FILE CHANGES ====================
    header "━━━ 📝 RECENT FILE CHANGES (Last 5 min) ━━━"
    echo ""

    local changes=$(get_recent_changes)
    if [ -n "$changes" ]; then
        echo "$changes" | while read -r file; do
            if [ -n "$file" ]; then
                local rel_path=${file#$DEV_DIR/}
                local mod_time=$(stat -f "%Sm" -t "%H:%M:%S" "$file" 2>/dev/null)
                echo -e "${GREEN}●${NC} ${GRAY}[${mod_time}]${NC} ${rel_path}"
            fi
        done
    else
        info "No recent changes"
    fi
    echo ""

    hr

    # ==================== SECTION 5: GIT ACTIVITY ====================
    header "━━━ 📦 RECENT GIT ACTIVITY ━━━"
    echo ""

    local git_activity=$(get_git_activity)
    if [ -n "$git_activity" ]; then
        echo "$git_activity" | head -5 | while IFS='|' read -r repo time msg; do
            if [ -n "$repo" ]; then
                echo -e "${YELLOW}⎇${NC} ${WHITE}${repo}${NC}"
                echo -e "   ${GRAY}└─${NC} ${time} - ${msg}"
                echo ""
            fi
        done
    else
        info "No recent git activity"
        echo ""
    fi

    hr

    # ==================== SECTION 6: SYSTEM RESOURCES ====================
    header "━━━ 💻 SYSTEM RESOURCES ━━━"
    echo ""

    # CPU and Memory for Claude processes
    local total_cpu=0
    local total_mem=0

    get_claude_sessions | while read -r line; do
        local cpu=$(echo "$line" | awk '{print $3}')
        local mem=$(echo "$line" | awk '{print $4}')
        total_cpu=$(echo "$total_cpu + $cpu" | bc 2>/dev/null || echo "0")
        total_mem=$(echo "$total_mem + $mem" | bc 2>/dev/null || echo "0")
    done

    echo -e "${CYAN}Claude Processes:${NC}"
    echo -e "   Total CPU: ${YELLOW}~${total_cpu}%${NC}"
    echo -e "   Total Memory: ${YELLOW}~${total_mem}%${NC}"
    echo ""

    hr

    # Footer
    echo -e "${GRAY}Press Ctrl+C to exit | Refreshing every 5 seconds...${NC}"
}

# Main loop
main() {
    echo "Starting live monitor..."
    sleep 1

    while true; do
        display_dashboard
        sleep 5
    done
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${GREEN}Monitor stopped.${NC}"; exit 0' INT

main
