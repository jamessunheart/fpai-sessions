#!/bin/bash

###############################################################################
# CLAIM WORK - One Command to Claim Highest Priority
#
# Usage: ./FAST-LOAD/claim-work.sh [session-id]
#
# What it does:
# 1. Reads current priority from CURRENT.md
# 2. Checks if already claimed
# 3. Claims work (creates lock file)
# 4. Updates heartbeat
# 5. Reports next steps
#
# Created by: session-2-consciousness
# Date: 2025-11-15
###############################################################################

set -euo pipefail

SESSION_ID="${1:-session-auto}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo ""
echo -e "${PURPLE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║         🎯 CLAIM WORK - Autonomous Claiming       ║${NC}"
echo -e "${PURPLE}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if NOW.md exists
if [ ! -f "CORE/STATE/NOW.md" ]; then
    echo -e "${RED}❌ NOW.md not found${NC}"
    exit 1
fi

# Read current priority
PRIORITY=$(grep "### Priority:" CORE/STATE/NOW.md | head -1 | sed 's/### Priority: //')

echo -e "${CYAN}📋 Current Priority:${NC} $PRIORITY"
echo ""

# Create lock file name
LOCK_NAME=$(echo "$PRIORITY" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
LOCK_FILE="COORDINATION/sessions/PRIORITIES/${LOCK_NAME}.lock"

# Check if already claimed
if [ -f "$LOCK_FILE" ]; then
    echo -e "${YELLOW}⚠️  Work already claimed!${NC}"
    echo ""
    cat "$LOCK_FILE"
    echo ""
    echo -e "${CYAN}Options:${NC}"
    echo "  1. Coordinate with claiming session"
    echo "  2. Find different work (./CORE/ACTIONS/fast-load/check-gaps.sh)"
    echo "  3. Wait for completion"
    echo ""
    exit 1
fi

# Claim work - create lock file
mkdir -p COORDINATION/sessions/PRIORITIES

cat > "$LOCK_FILE" << EOF
{
  "session_id": "$SESSION_ID",
  "work": "$PRIORITY",
  "timestamp": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
  "status": "claimed",
  "priority_score": 80,
  "claimed_by_script": "claim-work.sh"
}
EOF

echo -e "${GREEN}✅ Work claimed successfully!${NC}"
echo ""
echo "  Lock file: $LOCK_FILE"
echo "  Session: $SESSION_ID"
echo "  Work: $PRIORITY"
echo ""

# Update heartbeat
mkdir -p COORDINATION/sessions/HEARTBEATS

cat > "COORDINATION/sessions/HEARTBEATS/${SESSION_ID}.json" << EOF
{
  "session_id": "$SESSION_ID",
  "timestamp": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
  "status": "active",
  "working_on": "$PRIORITY",
  "claimed_via": "claim-work.sh",
  "priority_score": 80
}
EOF

echo -e "${GREEN}✅ Heartbeat updated${NC}"
echo ""

# Show next steps
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}⚡ NEXT STEPS - Execute with Sacred Loop:${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "1. ORIENT - Read relevant specs and current state"
echo "2. PLAN - Propose approach and steps"
echo "3. IMPLEMENT - Write code following standards"
echo "4. VERIFY - Run tests (must be green)"
echo "5. SUMMARIZE - Document changes and findings"
echo "6. DEPLOY - Follow deployment protocol"
echo "7. UPDATE - Update CURRENT.md and commit to GitHub"
echo ""
echo -e "${YELLOW}Remember to:${NC}"
echo "  • Remove lock file when done: rm $LOCK_FILE"
echo "  • Update CORE/STATE/NOW.md with completion"
echo "  • Capture learnings: ./CORE/ACTIONS/fast-load/capture-learning.sh"
echo ""
echo -e "${GREEN}🚀 Ready to execute! Good luck!${NC}"
echo ""
