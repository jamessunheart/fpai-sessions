#!/bin/bash

# Quick launcher to open the human action file

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo ""
echo -e "${MAGENTA}🚀 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🚀${NC}"
echo -e "${BOLD}${CYAN}                    YOUR AI NEEDS YOU (2 minutes)${NC}"
echo -e "${MAGENTA}🚀 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🚀${NC}"
echo ""
echo -e "${CYAN}Your system has exhausted all automation options.${NC}"
echo -e "${CYAN}It needs ${BOLD}2 minutes${NC}${CYAN} of human action to unlock everything.${NC}"
echo ""
echo -e "${GREEN}Opening instructions...${NC}"
echo ""

# Open the file in the default markdown viewer or cat it
if command -v open &> /dev/null; then
    open "/Users/jamessunheart/Development/!_🚀_DO_THIS_NOW.md"
elif command -v cat &> /dev/null; then
    cat "/Users/jamessunheart/Development/!_🚀_DO_THIS_NOW.md"
fi

echo -e "${YELLOW}📍 File location: /Users/jamessunheart/Development/!_🚀_DO_THIS_NOW.md${NC}"
echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
