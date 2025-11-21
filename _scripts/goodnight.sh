#!/bin/bash
# Good Night - Start overnight monitoring in one command
# Built by: Forge (Session #1)

GREEN='\033[0;32m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${MAGENTA}    GOOD NIGHT - STARTING OVERNIGHT SYSTEMS${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Stop any existing monitoring
pkill -f while-you-sleep 2>/dev/null

# Start overnight monitoring in background
echo -e "${CYAN}Starting overnight monitoring...${NC}"
nohup ./while-you-sleep.sh > /dev/null 2>&1 &
sleep 2

# Check if running
if ps aux | grep -v grep | grep while-you-sleep >/dev/null; then
    echo -e "${GREEN}✅ Overnight monitoring is running!${NC}"
    echo ""
    echo -e "${CYAN}While you sleep, the AI will:${NC}"
    echo "  • Monitor all services (every 15 min)"
    echo "  • Simulate treasury growth"
    echo "  • Track I MATCH readiness"
    echo "  • Generate morning report (6-8 AM)"
    echo "  • Learn and optimize"
    echo ""
    echo -e "${BOLD}${GREEN}Sleep well! Your morning report will be ready when you wake up.${NC}"
    echo ""
    echo -e "${CYAN}Morning commands:${NC}"
    echo "  cat overnight-logs/morning-report-\$(date +%Y-%m-%d).txt"
    echo "  ./activate-revenue.sh"
    echo ""
else
    echo -e "${RED}❌ Failed to start monitoring${NC}"
    echo "Try running manually: ./while-you-sleep.sh"
    echo ""
    exit 1
fi

echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BOLD}Good night! 😴💙${NC}"
echo ""
