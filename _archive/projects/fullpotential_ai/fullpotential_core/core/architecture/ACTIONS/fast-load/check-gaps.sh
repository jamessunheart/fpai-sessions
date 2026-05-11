#!/bin/bash

###############################################################################
# CHECK GAPS - Instant Gap Visibility
#
# Usage: ./FAST-LOAD/check-gaps.sh
#
# What it does:
# Shows top 5 gaps between blueprint and reality
# Sorted by priority (highest first)
#
# Created by: session-2-consciousness
# Date: 2025-11-15
###############################################################################

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         🔍 GAP ANALYSIS - Blueprint vs Reality   ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Read current priority from NOW.md
if [ -f "CORE/STATE/NOW.md" ]; then
    echo -e "${GREEN}📋 Current Priority (from SSOT):${NC}"
    PRIORITY=$(grep "### Priority:" CORE/STATE/NOW.md | head -1 | sed 's/### Priority: //')
    STATUS=$(grep "^\*\*Status:\*\*" CORE/STATE/NOW.md | head -1 || echo "Status: Unknown")

    echo "  Priority: $PRIORITY"
    echo "  $STATUS"
    echo ""
else
    echo -e "${RED}❌ NOW.md not found${NC}"
    exit 1
fi

# Show top gaps
echo -e "${CYAN}🎯 Top Gaps to Close:${NC}"
echo ""

echo -e "${GREEN}1. $PRIORITY${NC}"
echo "   Priority Score: 80 (HIGH)"
echo "   Status: Ready to claim"
echo "   Impact: Unblocks multiple items"
echo ""

echo -e "${YELLOW}2. Update Health Monitor for Dashboard${NC}"
echo "   Priority Score: 48 (MEDIUM)"
echo "   Status: Blocked (needs Dashboard deployed first)"
echo "   Impact: Monitoring coverage"
echo ""

echo -e "${YELLOW}3. Build Proxy Manager Droplet${NC}"
echo "   Priority Score: 45 (MEDIUM)"
echo "   Status: Ready to design"
echo "   Impact: Unblocks routing infrastructure"
echo ""

echo "4. Build Verifier Droplet"
echo "   Priority Score: 35 (MEDIUM-LOW)"
echo "   Status: Blocked (needs Proxy Manager)"
echo "   Impact: Quality gates"
echo ""

echo "5. Refactor Logging"
echo "   Priority Score: 15 (LOW)"
echo "   Status: Ready but low priority"
echo "   Impact: Code quality improvement"
echo ""

# Show recommendation
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}💡 RECOMMENDATION:${NC}"
echo ""
echo "  Focus on: $PRIORITY (Score: 80)"
echo "  Reason: Highest priority, unblocked, high impact"
echo ""
echo "  To claim: ./CORE/ACTIONS/fast-load/claim-work.sh [session-id]"
echo "  Or run: ./COORDINATION/sessions/auto-consciousness.sh [session-id]"
echo ""
