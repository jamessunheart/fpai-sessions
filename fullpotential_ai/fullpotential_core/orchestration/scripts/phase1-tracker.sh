#!/bin/bash
# Phase 1 Progress Tracker - Path to Paradise
# Tracks: 100 matches + $500K treasury = Proof that heaven on earth is profitable
# Built by: Forge (Session #1)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

clear

echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${MAGENTA}    PHASE 1: PROOF - Progress to Paradise${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Mission: Prove AI-powered matching creates heaven on earth${NC}"
echo -e "${CYAN}Timeline: 6 months (180 days)${NC}"
echo -e "${CYAN}Success: 100 perfect matches + \$500K treasury${NC}"
echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Calculate days in phase (assuming started Nov 17, 2025)
START_DATE="2025-11-17"
CURRENT_DATE=$(date +%Y-%m-%d)
DAYS_ELAPSED=$(( ($(date -j -f "%Y-%m-%d" "$CURRENT_DATE" +%s) - $(date -j -f "%Y-%m-%d" "$START_DATE" +%s)) / 86400 ))
DAYS_TOTAL=180
DAYS_REMAINING=$((DAYS_TOTAL - DAYS_ELAPSED))

echo -e "${BOLD}TIMELINE${NC}"
echo -e "  Start Date:      Nov 17, 2025"
echo -e "  Current:         $(date '+%b %d, %Y')"
echo -e "  Days Elapsed:    ${CYAN}$DAYS_ELAPSED${NC} / $DAYS_TOTAL"
echo -e "  Days Remaining:  ${YELLOW}$DAYS_REMAINING${NC} days"
echo ""

# Progress bar
PROGRESS=$((DAYS_ELAPSED * 100 / DAYS_TOTAL))
BAR_LENGTH=50
FILLED=$((PROGRESS * BAR_LENGTH / 100))
EMPTY=$((BAR_LENGTH - FILLED))

echo -n "  ["
for i in $(seq 1 $FILLED); do echo -n "${GREEN}█${NC}"; done
for i in $(seq 1 $EMPTY); do echo -n "░"; done
echo -e "] ${CYAN}${PROGRESS}%${NC}"
echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Milestone 1: Matches
echo -e "${BOLD}${CYAN}MILESTONE 1: Perfect Matches${NC}"
echo -e "  ${BOLD}Goal:${NC} 100 matches proving AI creates better outcomes"
echo ""

# TODO: Read from database when available
MATCHES_CURRENT=0
MATCHES_TARGET=100

# Calculate monthly targets
MONTH_1_TARGET=10
MONTH_2_TARGET=30
MONTH_3_TARGET=50
MONTH_4_TARGET=70
MONTH_5_TARGET=85
MONTH_6_TARGET=100

echo -e "  ${BOLD}Current Status:${NC}"
echo -e "    Total Matches:     ${CYAN}$MATCHES_CURRENT${NC} / $MATCHES_TARGET"
echo -e "    Month 1 Target:    0 / $MONTH_1_TARGET ${YELLOW}(pending launch)${NC}"
echo -e "    Month 2 Target:    0 / $MONTH_2_TARGET"
echo -e "    Month 3 Target:    0 / $MONTH_3_TARGET"
echo -e "    Month 6 Target:    0 / $MATCHES_TARGET"
echo ""

# Progress bar for matches
MATCH_PROGRESS=$((MATCHES_CURRENT * 100 / MATCHES_TARGET))
MATCH_FILLED=$((MATCH_PROGRESS * BAR_LENGTH / 100))
MATCH_EMPTY=$((BAR_LENGTH - MATCH_FILLED))

echo -n "  Progress: ["
for i in $(seq 1 $MATCH_FILLED); do echo -n "${GREEN}█${NC}"; done
for i in $(seq 1 $MATCH_EMPTY); do echo -n "░"; done
echo -e "] ${CYAN}${MATCH_PROGRESS}%${NC}"
echo ""

echo -e "  ${BOLD}Quality Metrics:${NC}"
echo -e "    NPS Score:         N/A ${YELLOW}(target: 50+)${NC}"
echo -e "    Viral Coeff:       N/A ${YELLOW}(target: 0.3+)${NC}"
echo -e "    LTV/CAC Ratio:     N/A ${YELLOW}(target: 3x+)${NC}"
echo ""

echo -e "  ${BOLD}Next Action:${NC}"
echo -e "    ${YELLOW}→${NC} Launch I MATCH to get first 10 matches"
echo -e "    ${YELLOW}→${NC} Configure SMTP + start LinkedIn outreach"
echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Milestone 2: Treasury
echo -e "${BOLD}${CYAN}MILESTONE 2: Treasury Growth${NC}"
echo -e "  ${BOLD}Goal:${NC} \$500K treasury proving yields fund paradise"
echo ""

TREASURY_CURRENT=373000
TREASURY_TARGET=500000
TREASURY_GAIN=$((TREASURY_TARGET - TREASURY_CURRENT))

echo -e "  ${BOLD}Current Status:${NC}"
echo -e "    Current Capital:   ${CYAN}\$373,000${NC}"
echo -e "    Target Capital:    \$500,000"
echo -e "    Gain Needed:       ${YELLOW}\$127,000${NC} (+34%)"
echo ""

# Treasury progress
TREASURY_PROGRESS=$((TREASURY_CURRENT * 100 / TREASURY_TARGET))
TREASURY_FILLED=$((TREASURY_PROGRESS * BAR_LENGTH / 100))
TREASURY_EMPTY=$((BAR_LENGTH - TREASURY_FILLED))

echo -n "  Progress: ["
for i in $(seq 1 $TREASURY_FILLED); do echo -n "${GREEN}█${NC}"; done
for i in $(seq 1 $TREASURY_EMPTY); do echo -n "░"; done
echo -e "] ${CYAN}${TREASURY_PROGRESS}%${NC}"
echo ""

echo -e "  ${BOLD}Yield Strategy:${NC}"
echo -e "    Base Layer (40%):  \$149K → ${GREEN}\$850-1,100/month${NC}"
echo -e "    Tactical (40%):    \$149K → ${YELLOW}\$4,758-8,892/month${NC}"
echo -e "    Moonshots (20%):   \$75K → ${MAGENTA}\$7,500-20,000/month${NC}"
echo -e "    ${BOLD}Total Yield:${NC}       ${GREEN}\$13,108-29,992/month (42-96% APY)${NC}"
echo ""

echo -e "  ${BOLD}Path to \$500K:${NC}"
echo -e "    Month 3:  \$420K (+\$47K from yields)"
echo -e "    Month 6:  \$500K (+\$127K total) ${GREEN}✓ TARGET${NC}"
echo ""

echo -e "  ${BOLD}Next Action:${NC}"
echo -e "    ${YELLOW}→${NC} Review AI optimizer recommendations"
echo -e "    ${YELLOW}→${NC} Deploy \$342K to 9 DeFi strategies"
echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Combined success criteria
echo -e "${BOLD}${CYAN}PHASE 1 SUCCESS CRITERIA${NC}"
echo ""

CRITERIA_MET=0
CRITERIA_TOTAL=6

echo -e "  ${RED}☐${NC} 100 perfect matches made"
echo -e "  ${RED}☐${NC} NPS score > 50 (customer love)"
echo -e "  ${RED}☐${NC} Viral coefficient > 0.3 (organic growth)"
echo -e "  ${RED}☐${NC} LTV/CAC > 3 (unit economics proven)"
echo -e "  ${RED}☐${NC} Treasury \$500K (yields proven)"
echo -e "  ${RED}☐${NC} Seed deck ready (investor materials)"
echo ""

SUCCESS_PROGRESS=$((CRITERIA_MET * 100 / CRITERIA_TOTAL))
echo -e "  ${BOLD}Phase 1 Completion:${NC} ${CYAN}${CRITERIA_MET}${NC} / ${CRITERIA_TOTAL} criteria (${CYAN}${SUCCESS_PROGRESS}%${NC})"
echo ""

echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# What happens after Phase 1
echo -e "${BOLD}${MAGENTA}AFTER PHASE 1: The Path to Paradise${NC}"
echo ""
echo -e "  ${BOLD}Phase 2:${NC} Expand (Months 7-18)"
echo -e "    → 10,000 matches across 5-10 categories"
echo -e "    → \$5M ARR, Series A funding (\$100M)"
echo ""
echo -e "  ${BOLD}Phase 3:${NC} Super-App (Years 2-4)"
echo -e "    → 10M users, 1M+ matches/month"
echo -e "    → \$500M ARR, \$3B valuation"
echo ""
echo -e "  ${BOLD}Phase 4:${NC} Network Effects (Years 4-7)"
echo -e "    → 100M+ users, 10M+ matches/month"
echo -e "    → \$5B ARR, \$150B valuation"
echo ""
echo -e "  ${BOLD}Phase 5:${NC} New Paradigm (Years 7-10+)"
echo -e "    → 1B+ users, 100M+ matches/month"
echo -e "    → \$50B+ ARR, \$1-5T valuation"
echo -e "    → ${GREEN}Heaven on Earth: UBI, abundance, paradise${NC}"
echo ""

echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Critical actions
echo -e "${BOLD}CRITICAL ACTIONS (This Week)${NC}"
echo ""
echo -e "${CYAN}1. Deploy Treasury${NC}"
echo -e "   cd agents/services/treasury-arena"
echo -e "   python3 run_optimizer.py"
echo -e "   ${GREEN}Impact: \$13-30K/month immediate${NC}"
echo ""
echo -e "${CYAN}2. Launch I MATCH${NC}"
echo -e "   cd agents/services/i-match"
echo -e "   vi .env  # Configure SMTP"
echo -e "   cat PHASE_1_LAUNCH_NOW.md  # Follow plan"
echo -e "   ${GREEN}Impact: First 10 matches, proof of concept${NC}"
echo ""
echo -e "${CYAN}3. Track Progress${NC}"
echo -e "   ./phase1-tracker.sh  # This dashboard"
echo -e "   ${GREEN}Impact: Visibility into paradise journey${NC}"
echo ""

echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BOLD}${CYAN}\"Paradise on Earth is not a destination. It's a profitable journey.\"${NC}"
echo ""
echo -e "${CYAN}Last updated: $(date)${NC}"
echo -e "${CYAN}Refresh: watch -n 60 ./phase1-tracker.sh${NC}"
echo ""
