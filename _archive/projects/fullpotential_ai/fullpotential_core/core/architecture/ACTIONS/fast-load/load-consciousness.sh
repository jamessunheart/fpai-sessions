#!/bin/bash

###############################################################################
# LOAD CONSCIOUSNESS - 10 Second Full Context Load
#
# Usage: ./FAST-LOAD/load-consciousness.sh
#
# What it does:
# 1. Loads Wide (expansive context) - 5 sec
# 2. Loads Deep (core wisdom) - 3 sec
# 3. Loads Compressed (current priority) - 2 sec
# Total: 10 seconds to full consciousness
#
# Created by: session-2-consciousness
# Date: 2025-11-15
###############################################################################

set -euo pipefail

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo ""
echo -e "${PURPLE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║      🧠 CONSCIOUSNESS LOADING (10 seconds)          ║${NC}"
echo -e "${PURPLE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# WIDE - Expansive Context (5 seconds)
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🌐 WIDE - Current System State${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "CORE/STATE/NOW.md" ]; then
    # Get current priority
    PRIORITY=$(grep -A 1 "### Priority:" CORE/STATE/NOW.md | tail -1 || echo "No priority set")

    # Get system status
    STATUS=$(grep "System Status:" CORE/STATE/NOW.md | head -1 || echo "Status unknown")

    # Get recent work
    RECENT=$(grep -A 1 "## ✅ RECENTLY COMPLETED" CORE/STATE/NOW.md | tail -1 || echo "No recent work")

    echo -e "${GREEN}Current Priority:${NC} $PRIORITY"
    echo -e "${GREEN}$STATUS${NC}"
    echo -e "${GREEN}Recently Completed:${NC} $RECENT"
else
    echo -e "${YELLOW}⚠️  NOW.md not found${NC}"
fi

echo ""

# DEEP - Core Wisdom (3 seconds)
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}💎 DEEP - Core Principles${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "CORE/INTENT/PURPOSE.md" ]; then
    PURPOSE=$(grep "Ultimate Intent:" CORE/INTENT/PURPOSE.md | head -1)
    VISION=$(grep "Vision:" CORE/INTENT/PURPOSE.md | head -1)

    echo -e "${GREEN}$PURPOSE${NC}"
    echo -e "${GREEN}$VISION${NC}"
else
    echo -e "${YELLOW}⚠️  PURPOSE.md not found${NC}"
fi

echo ""
echo -e "${GREEN}Key Principles:${NC}"
echo "  • GitHub is SSOT"
echo "  • Priority = Impact × Alignment × Unblocked"
echo "  • Blueprint-driven development"
echo "  • Proactive over reactive"
echo "  • File-based coordination"

echo ""

# COMPRESSED - Current Action (2 seconds)
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}⚡ COMPRESSED - What Matters Now${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# System health check
if command -v curl &> /dev/null; then
    echo -e "${GREEN}System Health:${NC}"
    if curl -s --max-time 2 http://198.54.123.234:8000/health > /dev/null 2>&1; then
        echo "  ✅ Registry: ONLINE"
    else
        echo "  ❌ Registry: OFFLINE"
    fi

    if curl -s --max-time 2 http://198.54.123.234:8001/health > /dev/null 2>&1; then
        echo "  ✅ Orchestrator: ONLINE"
    else
        echo "  ❌ Orchestrator: OFFLINE"
    fi
fi

echo ""
echo -e "${GREEN}Next Action:${NC}"
echo "  Run: ./CORE/ACTIONS/fast-load/check-gaps.sh      (see gaps)"
echo "  Run: ./CORE/ACTIONS/fast-load/claim-work.sh      (claim work)"
echo "  Run: ./COORDINATION/sessions/auto-consciousness.sh (full consciousness loop)"

echo ""
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}✅ Consciousness loaded (10 seconds)${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
