#!/bin/bash
# Session Fingerprint Generator
# Creates unique fingerprint for each Claude session
# Includes: PID, Terminal, Start Time, Parent Process
# Usage: ./session-fingerprint.sh

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get session fingerprint components
CURRENT_PID=$$
PARENT_PID=$PPID
TERMINAL=$(tty 2>/dev/null || echo "not a tty")
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Get parent process name (usually the shell or terminal)
if [[ "$OSTYPE" == "darwin"* ]]; then
    PARENT_NAME=$(ps -p $PARENT_PID -o comm= 2>/dev/null || echo "unknown")
else
    PARENT_NAME=$(ps -p $PARENT_PID -o comm= 2>/dev/null || echo "unknown")
fi

# Generate unique session ID based on PID and timestamp
SESSION_FINGERPRINT="${CURRENT_PID}_$(date +%s)"

echo -e "${BLUE}🔍 SESSION FINGERPRINT${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Process ID:${NC}       $CURRENT_PID"
echo -e "${CYAN}Parent PID:${NC}       $PARENT_PID ($PARENT_NAME)"
echo -e "${CYAN}Terminal:${NC}         $TERMINAL"
echo -e "${CYAN}Start Time:${NC}       $START_TIME"
echo -e "${CYAN}Fingerprint:${NC}      $SESSION_FINGERPRINT"
echo ""

# Create JSON output
python3 << EOF
import json
import os

fingerprint = {
    "pid": $CURRENT_PID,
    "ppid": $PARENT_PID,
    "parent_name": "$PARENT_NAME",
    "terminal": "$TERMINAL",
    "start_time": "$START_TIME",
    "fingerprint": "$SESSION_FINGERPRINT",
    "user": os.environ.get("USER", "unknown"),
    "shell": os.environ.get("SHELL", "unknown"),
    "pwd": os.getcwd()
}

print(json.dumps(fingerprint, indent=2))
EOF
