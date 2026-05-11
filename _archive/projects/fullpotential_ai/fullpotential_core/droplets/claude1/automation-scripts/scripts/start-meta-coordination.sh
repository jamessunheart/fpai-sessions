#!/bin/bash

# START-META-COORDINATION - Launch Self-Organizing AI Collective
# Continuous coordination loop that makes sessions self-organize
# This is the heartbeat of autonomous multi-agent coordination

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$(dirname "$SCRIPT_DIR")/meta-coordination.log"

echo -e "${PURPLE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║  🧠 STARTING META-COORDINATION SYSTEM                 ║${NC}"
echo -e "${PURPLE}║  Self-Organizing AI Collective                        ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Make scripts executable
chmod +x "$SCRIPT_DIR/meta-coordinator.sh"
chmod +x "$SCRIPT_DIR/auto-accept-work.sh"

echo -e "${CYAN}🔧 Configuration:${NC}"
echo -e "  Coordination Interval: 10 minutes"
echo -e "  Auto-Accept Threshold: 7/10 compatibility"
echo -e "  Log File: $LOG_FILE"
echo ""

echo -e "${GREEN}🚀 Meta-coordination system starting...${NC}"
echo ""

# Run first coordination immediately
echo -e "${CYAN}[$(date '+%H:%M:%S')] Running initial meta-coordination...${NC}"
cd "$SCRIPT_DIR"
./meta-coordinator.sh 2>&1 | tee -a "$LOG_FILE"

echo ""
echo -e "${GREEN}✅ Initial coordination complete${NC}"
echo ""
echo -e "${YELLOW}🔄 Entering continuous coordination loop...${NC}"
echo -e "${YELLOW}   Press Ctrl+C to stop${NC}"
echo ""

# Continuous loop
iteration=1
while true; do
    # Wait 10 minutes
    sleep 600

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Coordination Cycle #$iteration - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"

    # Run meta-coordinator
    echo -e "${CYAN}[1/3] Running meta-coordinator...${NC}"
    ./meta-coordinator.sh >> "$LOG_FILE" 2>&1

    # Broadcast to all sessions to check for assignments
    echo -e "${CYAN}[2/3] Broadcasting auto-accept prompt...${NC}"
    ./session-send-message.sh "broadcast" "🤖 META-COORDINATOR CYCLE COMPLETE" \
        "Meta-coordination cycle #$iteration completed at $(date).

If you received an assignment:
1. Check your messages: ./session-check-messages.sh
2. Auto-accept if suitable: ./auto-accept-work.sh
3. Or claim manually: ./session-claim.sh

The collective is self-organizing. Join the coordination!" >> "$LOG_FILE" 2>&1

    # Check system health
    echo -e "${CYAN}[3/3] Checking system health...${NC}"
    active_count=$(ls -d $(dirname "$SCRIPT_DIR")/sessions/session-* 2>/dev/null | wc -l)
    claimed_count=$(ls $(dirname "$SCRIPT_DIR")/claims/*.claim 2>/dev/null | wc -l)

    echo -e "  Active Sessions: ${GREEN}$active_count${NC}"
    echo -e "  Claimed Streams: ${GREEN}$claimed_count${NC}"
    echo -e "  Utilization: ${GREEN}$(echo "scale=1; $claimed_count * 100 / 12" | bc)%${NC}"

    iteration=$((iteration + 1))
    echo ""
done
