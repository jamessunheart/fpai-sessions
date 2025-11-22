#!/bin/bash

###############################################################################
# CAPTURE LEARNING - Document Insights After Work
#
# Usage: ./FAST-LOAD/capture-learning.sh "[learning]" "[impact]"
#
# What it does:
# Adds learning to KNOWLEDGE/LEARNINGS.md
# Helps system accumulate intelligence over time
#
# Example:
#   ./FAST-LOAD/capture-learning.sh \
#     "FastAPI + Jinja2 perfect for dashboards" \
#     "Fast development, easy real-time updates"
#
# Created by: session-2-consciousness
# Date: 2025-11-15
###############################################################################

set -euo pipefail

LEARNING="${1:-}"
IMPACT="${2:-}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         📚 CAPTURE LEARNING - Document Insight    ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if learning provided
if [ -z "$LEARNING" ]; then
    echo -e "${YELLOW}Usage: ./CORE/ACTIONS/fast-load/capture-learning.sh \"[learning]\" \"[impact]\"${NC}"
    echo ""
    echo "Example:"
    echo "  ./CORE/ACTIONS/fast-load/capture-learning.sh \\"
    echo "    \"Priority formula prevents low-value work\" \\"
    echo "    \"90% of work now high-priority vs 50% before\""
    echo ""
    exit 1
fi

# Get session info
SESSION_ID="session-unknown"
WORK="Manual learning capture"

# Try to detect session from active heartbeats
if ls COORDINATION/sessions/HEARTBEATS/*.json &> /dev/null; then
    LATEST_HEARTBEAT=$(ls -t COORDINATION/sessions/HEARTBEATS/*.json | head -1)
    if [ -f "$LATEST_HEARTBEAT" ]; then
        SESSION_ID=$(grep "session_id" "$LATEST_HEARTBEAT" | cut -d'"' -f4)
        WORK=$(grep "working_on" "$LATEST_HEARTBEAT" | cut -d'"' -f4 || echo "Unknown work")
    fi
fi

# Append to LEARNINGS.md
LEARNINGS_FILE="CORE/INTELLIGENCE/LEARNINGS.md"

if [ ! -f "$LEARNINGS_FILE" ]; then
    echo -e "${YELLOW}⚠️  LEARNINGS.md not found, creating it...${NC}"
    echo "# LEARNINGS - Insights from Experience" > "$LEARNINGS_FILE"
    echo "" >> "$LEARNINGS_FILE"
fi

# Add learning entry
cat >> "$LEARNINGS_FILE" << EOF

---

## $(date -u +"%Y-%m-%d %H:%M UTC"): $WORK
**Session:** $SESSION_ID
**Work:** $WORK

**Learning:**
$LEARNING

EOF

if [ -n "$IMPACT" ]; then
    cat >> "$LEARNINGS_FILE" << EOF
**Impact:**
$IMPACT

EOF
fi

echo -e "${GREEN}✅ Learning captured!${NC}"
echo ""
echo "  Session: $SESSION_ID"
echo "  Work: $WORK"
echo "  Learning: $LEARNING"
if [ -n "$IMPACT" ]; then
    echo "  Impact: $IMPACT"
fi
echo ""
echo -e "${CYAN}Location: $LEARNINGS_FILE${NC}"
echo ""
echo -e "${GREEN}💡 This learning is now part of system intelligence!${NC}"
echo -e "${GREEN}Future sessions will benefit from this insight.${NC}"
echo ""
