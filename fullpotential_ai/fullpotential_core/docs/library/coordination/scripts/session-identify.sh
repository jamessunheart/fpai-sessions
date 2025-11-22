#!/bin/bash
# Session Identity Detection & Registration
# Auto-detects or prompts for session identity on startup
# Version: 2.1 (Added chronological auto-assignment)
# Usage: source this in .bashrc or run manually

SESSION_DIR="/Users/jamessunheart/Development/docs/coordination"
SESSIONS_FILE="$SESSION_DIR/claude_sessions.json"
IDENTITY_FILE="$SESSION_DIR/.session_identity"
HEARTBEATS_DIR="$SESSION_DIR/heartbeats"
CLEANUP_SCRIPT="$SESSION_DIR/scripts/session-cleanup-stale.sh"

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function show_banner() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   FPAI SESSION IDENTITY SYSTEM${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

function load_identity() {
    # Check if identity file exists and is recent (created today)
    if [ -f "$IDENTITY_FILE" ]; then
        # Check if file was modified today
        if [ "$(date +%Y-%m-%d)" = "$(date -r "$IDENTITY_FILE" +%Y-%m-%d)" ]; then
            cat "$IDENTITY_FILE"
            return 0
        fi
    fi
    return 1
}

function save_identity() {
    local number=$1
    echo "$number" > "$IDENTITY_FILE"
}

function show_registered_sessions() {
    echo -e "${YELLOW}Currently Registered Sessions:${NC}"
    echo ""

    python3 << 'EOPYTHON'
import json
import sys

try:
    with open("/Users/jamessunheart/Development/docs/coordination/claude_sessions.json", 'r') as f:
        sessions = json.load(f)

    for num in sorted(sessions.keys(), key=int):
        session = sessions[num]
        role = session.get('role', 'Unknown')
        status = session.get('status', 'unknown')
        status_icon = '✅' if status == 'active' else '⏸️'
        print(f"  {status_icon} #{num:2s} - {role}")

    print()
    taken_numbers = set(int(k) for k in sessions.keys())
    available = [i for i in range(1, 14) if i not in taken_numbers]

    if available:
        print(f"Available numbers: {', '.join(map(str, available))}")
    else:
        print("All session slots (1-13) are taken!")

except FileNotFoundError:
    print("  No sessions registered yet.")
    print("  Available numbers: 1-13")
except Exception as e:
    print(f"  Error reading sessions: {e}")
EOPYTHON
}

function get_session_info() {
    local number=$1

    python3 << EOPYTHON
import json
import sys

try:
    with open("$SESSIONS_FILE", 'r') as f:
        sessions = json.load(f)

    if "$number" in sessions:
        session = sessions["$number"]
        print(f"Number: {session['number']}")
        print(f"Role: {session['role']}")
        print(f"Goal: {session['goal']}")
        print(f"Session ID: {session['session_id']}")
        print(f"Status: {session['status']}")
    else:
        sys.exit(1)
except:
    sys.exit(1)
EOPYTHON
}

function get_next_available_number() {
    # Returns the lowest available number (1-13) based on active sessions
    python3 << 'EOPYTHON'
import json

try:
    with open("/Users/jamessunheart/Development/docs/coordination/claude_sessions.json", 'r') as f:
        sessions = json.load(f)

    # Get all active session numbers
    active_numbers = set()
    for num, session in sessions.items():
        if session.get('status') == 'active':
            active_numbers.add(int(num))

    # Find lowest available number (1-13)
    for i in range(1, 14):
        if i not in active_numbers:
            print(i)
            break
    else:
        # All taken, return next number
        print(14)

except FileNotFoundError:
    # No sessions yet, start with 1
    print(1)
except Exception as e:
    print(1)
EOPYTHON
}

function send_heartbeat() {
    local session_num=$1
    mkdir -p "$HEARTBEATS_DIR"

    local timestamp=$(date +%Y-%m-%d_%H-%M-%S)
    local heartbeat_file="$HEARTBEATS_DIR/${timestamp}-session-${session_num}.json"

    cat > "$heartbeat_file" << EOF
{
  "session_number": $session_num,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "type": "identity_heartbeat",
  "source": "session-identify.sh"
}
EOF

    echo -e "${CYAN}💓 Heartbeat sent${NC}"
}

function check_stale_sessions() {
    # Returns count of stale sessions
    if [ ! -f "$CLEANUP_SCRIPT" ]; then
        echo "0"
        return
    fi

    # Run cleanup in dry-run mode and parse output
    local output=$("$CLEANUP_SCRIPT" --dry-run 2>/dev/null)
    local stale_count=$(echo "$output" | grep "💤 Stale sessions:" | awk '{print $4}')

    echo "${stale_count:-0}"
}

function offer_cleanup() {
    local stale_count=$(check_stale_sessions)

    if [ "$stale_count" -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Detected $stale_count stale session(s) (no recent heartbeat)${NC}"
        echo ""
        echo -e "${CYAN}Would you like to clean up stale sessions first?${NC}"
        echo -e "  This will mark inactive sessions so you can reuse their numbers."
        echo ""
        read -p "Clean up stale sessions? (y/n): " cleanup_choice

        if [ "$cleanup_choice" = "y" ] || [ "$cleanup_choice" = "Y" ]; then
            echo ""
            echo -e "${CYAN}Running cleanup...${NC}"
            "$CLEANUP_SCRIPT"
            echo ""
            echo -e "${GREEN}✅ Cleanup complete! Registry refreshed.${NC}"
            echo ""
            return 0
        else
            echo ""
            echo -e "${YELLOW}Skipping cleanup. Continuing with current registry.${NC}"
            echo ""
            return 1
        fi
    fi

    return 1
}

function prompt_for_identity() {
    echo -e "${YELLOW}Session identity not found or expired.${NC}"
    echo ""
    show_registered_sessions
    echo ""

    # Get next available number chronologically
    local next_num=$(get_next_available_number)

    echo -e "${GREEN}🎯 Auto-assigning Session #${next_num}${NC} ${CYAN}(next available chronologically)${NC}"
    echo ""
    echo -e "  ${BLUE}[Enter]${NC} Accept Session #${next_num}"
    echo -e "  ${BLUE}[1-13]${NC} Choose different number (override)"
    echo -e "  ${BLUE}[skip]${NC}  Skip identification (not recommended)"
    echo ""
    read -p "Accept #${next_num}? [Enter to accept]: " choice

    # If empty, use auto-assigned number
    if [ -z "$choice" ]; then
        choice="$next_num"
    fi

    case "$choice" in
        [1-9]|1[0-3])
            # Check if this number is already active
            local is_active=$(python3 << EOPYTHON
import json
try:
    with open("$SESSIONS_FILE", 'r') as f:
        sessions = json.load(f)
    if "$choice" in sessions and sessions["$choice"].get("status") == "active":
        print("yes")
    else:
        print("no")
except:
    print("no")
EOPYTHON
)

            if [ "$is_active" = "yes" ]; then
                echo ""
                echo -e "${RED}❌ Session #$choice is already ACTIVE${NC}"
                echo -e "   ${YELLOW}Choose a different number or run cleanup first${NC}"
                echo ""
                return 1
            fi

            # Check if session exists in registry (might be inactive)
            if get_session_info "$choice" > /dev/null 2>&1; then
                echo ""
                echo -e "${GREEN}✅ Reactivating Session #$choice${NC}"
                echo ""
                get_session_info "$choice" | while IFS=: read -r key value; do
                    echo -e "  ${BLUE}$key:${NC}$value"
                done

                # Update status to active
                python3 << EOPYTHON
import json
with open("$SESSIONS_FILE", 'r') as f:
    sessions = json.load(f)
sessions["$choice"]["status"] = "active"
with open("$SESSIONS_FILE", 'w') as f:
    json.dump(sessions, f, indent=2)
EOPYTHON

                save_identity "$choice"
                export FPAI_SESSION_NUMBER="$choice"
                echo ""
                echo -e "${GREEN}Session identity saved for today.${NC}"
                send_heartbeat "$choice"
                return 0
            else
                # New session, needs registration
                echo ""
                echo -e "${YELLOW}Session #$choice not registered yet.${NC}"
                read -p "Role (e.g., 'Infrastructure Engineer'): " role
                read -p "Goal (e.g., 'Deploy and maintain core services'): " goal
                register_new_session "$choice" "$role" "$goal"
            fi
            ;;
        skip)
            echo -e "${YELLOW}⚠️  Running without session identity.${NC}"
            echo -e "   Some coordination features may not work."
            return 1
            ;;
        *)
            echo -e "${RED}Invalid choice.${NC}"
            return 1
            ;;
    esac
}

function register_new_session() {
    local suggested_number=$1
    local role=$2
    local goal=$3

    echo ""
    echo -e "${GREEN}Register New Session${NC}"
    echo ""

    if [ -z "$suggested_number" ]; then
        suggested_number=$(get_next_available_number)
        echo -e "${CYAN}Auto-assigning #${suggested_number}${NC}"
    fi

    if [ -z "$role" ]; then
        read -p "Role (e.g., 'Infrastructure Engineer'): " role
    fi

    if [ -z "$goal" ]; then
        read -p "Goal (e.g., 'Deploy and maintain core services'): " goal
    fi

    # Use registration script
    bash "$SESSION_DIR/scripts/claude-session-register.sh" "$suggested_number" "$role" "$goal"

    if [ $? -eq 0 ]; then
        save_identity "$suggested_number"
        export FPAI_SESSION_NUMBER="$suggested_number"
        send_heartbeat "$suggested_number"
        return 0
    else
        return 1
    fi
}

# Main execution
main() {
    show_banner

    # Offer to clean up stale sessions first
    offer_cleanup

    # Try to load existing identity
    if SESSION_NUM=$(load_identity); then
        echo -e "${GREEN}✅ Session Identity Loaded${NC}"
        echo ""
        if get_session_info "$SESSION_NUM" 2>/dev/null; then
            echo ""
            export FPAI_SESSION_NUMBER="$SESSION_NUM"
            echo -e "${BLUE}Environment variable set: FPAI_SESSION_NUMBER=$SESSION_NUM${NC}"

            # Send heartbeat for loaded session
            send_heartbeat "$SESSION_NUM"
        else
            echo -e "${YELLOW}⚠️  Cached identity (#$SESSION_NUM) not found in registry.${NC}"
            prompt_for_identity
        fi
    else
        # No cached identity, prompt user
        prompt_for_identity
    fi

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Export session number for use in other scripts
    if [ -n "$FPAI_SESSION_NUMBER" ]; then
        echo "export FPAI_SESSION_NUMBER=$FPAI_SESSION_NUMBER" > "$SESSION_DIR/.session_env"

        # Update .current_session file for backward compatibility
        echo "session-$FPAI_SESSION_NUMBER" > "$SESSION_DIR/.current_session"
    fi
}

# Run if executed directly (not sourced)
if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
    main
fi
