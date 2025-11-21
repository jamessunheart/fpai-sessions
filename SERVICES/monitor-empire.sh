#!/bin/bash
# 📊 Monitor FPAI Empire Status

clear
echo "📊 FPAI EMPIRE - LIVE MONITOR"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check FPAI Hub
echo -e "${BLUE}🌐 FPAI Hub${NC}"
if curl -s http://localhost:8010/health > /dev/null 2>&1; then
    echo -e "   Status: ${GREEN}RUNNING${NC}"
    echo "   URL: http://localhost:8010"
else
    echo -e "   Status: ${RED}DOWN${NC}"
fi
echo ""

# Check Agents
echo -e "${BLUE}🤖 Autonomous Agents${NC}"

declare -a AGENTS=(
    "defi_yield_agent:DeFi Yield Agent"
    "gas_optimizer_agent:Gas Optimizer"
    "arbitrage_agent:Arbitrage Agent"
    "human_recruiter_agent:Human Recruiter"
    "resource_monitor_agent:Resource Monitor"
)

for agent_info in "${AGENTS[@]}"; do
    IFS=':' read -r agent_proc agent_name <<< "$agent_info"

    if pgrep -f "$agent_proc" > /dev/null; then
        echo -e "   ${GREEN}●${NC} $agent_name: RUNNING"

        # Show last log line
        log_file="/tmp/${agent_proc}.log"
        if [ -f "$log_file" ]; then
            last_line=$(tail -1 "$log_file" 2>/dev/null | cut -c 1-70)
            echo "      └─ $last_line"
        fi
    else
        echo -e "   ${RED}○${NC} $agent_name: STOPPED"
    fi
done

echo ""

# Show Treasury Status (if FPAI Hub is running)
echo -e "${BLUE}💰 Treasury Status${NC}"
treasury_data=$(curl -s http://localhost:8010/api/treasury/status 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$treasury_data" | python3 -m json.tool 2>/dev/null | head -15 || echo "$treasury_data"
else
    echo "   Unable to fetch treasury data"
fi

echo ""

# Show recent agent activity
echo -e "${BLUE}📝 Recent Activity (Last 5 Minutes)${NC}"
echo ""

for agent_info in "${AGENTS[@]}"; do
    IFS=':' read -r agent_proc agent_name <<< "$agent_info"
    log_file="/tmp/${agent_proc}.log"

    if [ -f "$log_file" ]; then
        echo -e "${YELLOW}$agent_name:${NC}"
        tail -3 "$log_file" 2>/dev/null | while read line; do
            echo "   $line"
        done
        echo ""
    fi
done

echo ""
echo "========================================"
echo "Press Ctrl+C to exit, or run with 'watch' for continuous updates:"
echo "  watch -n 10 $0"
