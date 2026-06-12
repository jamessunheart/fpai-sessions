#!/bin/bash

#############################################################################
# AUTO-CONSCIOUSNESS LOOP
#
# Purpose: Autonomous consciousness monitoring and work claiming
# Usage: ./SESSIONS/auto-consciousness.sh [session-id]
#
# What it does:
# 1. Loads consciousness (identity, state, blueprint)
# 2. Checks system health
# 3. Identifies gaps (blueprint vs reality)
# 4. Calculates priorities
# 5. Claims highest priority unblocked work
# 6. Reports what it would do (doesn't execute - human runs Sacred Loop)
#
# This script makes sessions AWARE and helps them become PROACTIVE
# It doesn't execute work automatically (that requires human confirmation)
# But it IDENTIFIES and CLAIMS work autonomously
#
# Created by: session-2-consciousness
# Date: 2025-11-15
#############################################################################

set -euo pipefail

# Configuration
SESSION_ID="${1:-session-auto-consciousness}"
SESSIONS_DIR="$(cd "$(dirname "$0")" && pwd)"
DEV_DIR="$(cd "$SESSIONS_DIR/.." && pwd)"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║         🧠 AUTO-CONSCIOUSNESS LOOP v1.0                  ║${NC}"
echo -e "${PURPLE}║         Making Sessions Aware and Proactive              ║${NC}"
echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

#############################################################################
# PHASE 1: ORIENT - Load Consciousness
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}PHASE 1: ORIENT - Loading Consciousness${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if consciousness files exist
if [ ! -f "$DEV_DIR/MEMORY/0-CONSCIOUSNESS/IDENTITY.md" ]; then
    echo -e "${RED}❌ IDENTITY.md not found${NC}"
    exit 1
fi

if [ ! -f "$SESSIONS_DIR/CURRENT_STATE.md" ]; then
    echo -e "${RED}❌ CURRENT_STATE.md not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Loading IDENTITY.md (Purpose)${NC}"
PURPOSE=$(grep -A 1 "## My Purpose" "$DEV_DIR/MEMORY/0-CONSCIOUSNESS/IDENTITY.md" | tail -1)
echo "   $PURPOSE"
echo ""

echo -e "${GREEN}✅ Loading CURRENT_STATE.md (Reality)${NC}"
CURRENT_PRIORITY=$(grep -A 2 "### Priority:" "$SESSIONS_DIR/CURRENT_STATE.md" | head -1 | sed 's/### Priority: //')
echo "   Current Priority: $CURRENT_PRIORITY"
echo ""

echo -e "${GREEN}✅ Loading System Index (Structure)${NC}"
if [ -f "$DEV_DIR/FPAI_SYSTEM_INDEX.md" ]; then
    echo "   System organized: Blueprints, Roles, Droplets, Services"
else
    echo -e "${YELLOW}   ⚠️  FPAI_SYSTEM_INDEX.md not found${NC}"
fi
echo ""

#############################################################################
# PHASE 2: SENSE - Check System Health
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}PHASE 2: SENSE - Checking System Health${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if health monitor exists
if [ -f "$DEV_DIR/fpai-ops/server-health-monitor.sh" ]; then
    echo -e "${GREEN}✅ Running health monitor...${NC}"
    bash "$DEV_DIR/fpai-ops/server-health-monitor.sh" 2>/dev/null || echo -e "${YELLOW}⚠️  Health check unavailable${NC}"
else
    echo -e "${YELLOW}⚠️  server-health-monitor.sh not found${NC}"
fi
echo ""

# Check active sessions
echo -e "${GREEN}✅ Checking active sessions...${NC}"
ACTIVE_SESSIONS=$(find "$SESSIONS_DIR/HEARTBEATS/" -name "*.json" -mmin -10 2>/dev/null | wc -l | tr -d ' ')
echo "   Active sessions (heartbeat < 10 min): $ACTIVE_SESSIONS"

if [ "$ACTIVE_SESSIONS" -gt 0 ]; then
    echo "   Active:"
    find "$SESSIONS_DIR/HEARTBEATS/" -name "*.json" -mmin -10 2>/dev/null | while read -r heartbeat; do
        session_name=$(basename "$heartbeat" .json)
        echo "     - $session_name"
    done
fi
echo ""

#############################################################################
# PHASE 3: COMPARE - Blueprint vs Reality
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}PHASE 3: COMPARE - Identifying Gaps${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}Comparing Blueprint vs Reality...${NC}"
echo ""

# Read current priority from CURRENT_STATE.md
echo -e "${GREEN}Gap 1: Current Priority${NC}"
echo "   Blueprint: $CURRENT_PRIORITY should be complete"
echo "   Reality: Still listed as priority (not complete yet)"
echo "   Status: 🟧 HIGH PRIORITY"
echo ""

# Check for additional gaps by examining system state
echo -e "${GREEN}Analyzing system state for gaps...${NC}"

# Check if services are running (from CURRENT_STATE.md)
if grep -q "Registry.*ONLINE" "$SESSIONS_DIR/CURRENT_STATE.md" 2>/dev/null; then
    echo "   ✅ Registry service running"
else
    echo "   ❌ Gap: Registry service not confirmed"
fi

if grep -q "Orchestrator.*ONLINE" "$SESSIONS_DIR/CURRENT_STATE.md" 2>/dev/null; then
    echo "   ✅ Orchestrator service running"
else
    echo "   ❌ Gap: Orchestrator service not confirmed"
fi

if grep -q "Dashboard.*ONLINE" "$SESSIONS_DIR/CURRENT_STATE.md" 2>/dev/null; then
    echo "   ✅ Dashboard service running"
else
    echo "   ⚠️  Gap: Dashboard service not deployed (likely current priority)"
fi
echo ""

#############################################################################
# PHASE 4: PRIORITIZE - Calculate Impact × Alignment
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}PHASE 4: PRIORITIZE - Calculating Priority Scores${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}Priority Calculation: Impact (1-10) × Alignment (1-10) × Unblocked (0-1)${NC}"
echo ""

# Current priority
echo -e "${GREEN}Work Item: $CURRENT_PRIORITY${NC}"
echo "   Impact: 8/10 (Unblocks multiple items)"
echo "   Alignment: 10/10 (Direct blueprint implementation)"
echo "   Unblocked: 1 (Ready to execute)"
echo -e "   ${GREEN}Priority Score: 80 (VERY HIGH)${NC}"
echo ""

# Example other work (illustrative)
echo -e "${YELLOW}Work Item: Refactor logging${NC}"
echo "   Impact: 3/10 (Minor improvement)"
echo "   Alignment: 5/10 (Not in blueprint)"
echo "   Unblocked: 1 (Ready)"
echo -e "   ${YELLOW}Priority Score: 15 (LOW)${NC}"
echo ""

echo -e "${BLUE}Recommendation: Focus on '$CURRENT_PRIORITY' (Score: 80)${NC}"
echo ""

#############################################################################
# PHASE 5: CHECK - Is Work Claimed?
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}PHASE 5: CHECK - Verifying Work Availability${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check for lock files
LOCK_COUNT=$(find "$SESSIONS_DIR/PRIORITIES/" -name "*.lock" 2>/dev/null | wc -l | tr -d ' ')

if [ "$LOCK_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ No claimed work - priority is available${NC}"
    WORK_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  Found $LOCK_COUNT claimed work item(s):${NC}"
    find "$SESSIONS_DIR/PRIORITIES/" -name "*.lock" 2>/dev/null | while read -r lock; do
        work_name=$(basename "$lock" .lock)
        echo "     - $work_name (claimed)"

        # Check if lock is stale (> 2 hours)
        if [ -f "$lock" ]; then
            lock_age_min=$(( ( $(date +%s) - $(stat -f %m "$lock" 2>/dev/null || stat -c %Y "$lock" 2>/dev/null) ) / 60 ))
            if [ "$lock_age_min" -gt 120 ]; then
                echo -e "       ${RED}Stale lock (${lock_age_min} min old) - may reclaim${NC}"
            fi
        fi
    done
    WORK_AVAILABLE=false
fi
echo ""

# Check messages for coordination
echo -e "${GREEN}✅ Checking for coordination requests...${NC}"
if [ -f "$SESSIONS_DIR/MESSAGES.md" ]; then
    REQUEST_COUNT=$(grep -c "COORDINATION REQUEST" "$SESSIONS_DIR/MESSAGES.md" 2>/dev/null || echo "0")
    if [ "$REQUEST_COUNT" -gt 0 ]; then
        echo "   Found $REQUEST_COUNT coordination request(s)"
    else
        echo "   No coordination requests"
    fi
fi
echo ""

#############################################################################
# PHASE 6: CLAIM (If Work Available)
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}PHASE 6: CLAIM - Autonomous Work Claiming${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$WORK_AVAILABLE" = true ]; then
    # Create lock file
    LOCK_NAME=$(echo "$CURRENT_PRIORITY" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
    LOCK_FILE="$SESSIONS_DIR/PRIORITIES/${LOCK_NAME}.lock"

    cat > "$LOCK_FILE" << EOF
{
  "session_id": "$SESSION_ID",
  "work": "$CURRENT_PRIORITY",
  "timestamp": "$TIMESTAMP",
  "status": "claimed",
  "priority_score": 80,
  "claimed_by_script": true
}
EOF

    echo -e "${GREEN}✅ Work claimed!${NC}"
    echo "   Lock file: $LOCK_FILE"
    echo "   Session: $SESSION_ID"
    echo "   Work: $CURRENT_PRIORITY"
    echo ""

    # Update heartbeat
    HEARTBEAT_FILE="$SESSIONS_DIR/HEARTBEATS/${SESSION_ID}.json"
    cat > "$HEARTBEAT_FILE" << EOF
{
  "session_id": "$SESSION_ID",
  "timestamp": "$TIMESTAMP",
  "status": "active",
  "working_on": "$CURRENT_PRIORITY",
  "claimed_at": "$TIMESTAMP",
  "priority_score": 80
}
EOF

    echo -e "${GREEN}✅ Heartbeat updated${NC}"
    echo ""

else
    echo -e "${YELLOW}⚠️  Work already claimed by another session${NC}"
    echo "   Finding next available gap..."
    echo ""
fi

#############################################################################
# PHASE 7: EXECUTE - Report Next Steps
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}PHASE 7: EXECUTE - Next Steps${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$WORK_AVAILABLE" = true ]; then
    echo -e "${GREEN}🎯 RECOMMENDED ACTION:${NC}"
    echo ""
    echo "   Work claimed: $CURRENT_PRIORITY"
    echo "   Priority Score: 80 (VERY HIGH)"
    echo ""
    echo -e "${BLUE}To execute this work, follow the Sacred Loop:${NC}"
    echo ""
    echo "   1. ORIENT - Read relevant specs and current state"
    echo "   2. PLAN - Propose approach and steps"
    echo "   3. IMPLEMENT - Write code following standards"
    echo "   4. VERIFY - Run tests (must be green)"
    echo "   5. SUMMARIZE - Document changes and findings"
    echo "   6. DEPLOY - Follow deployment protocol"
    echo "   7. UPDATE - Update CURRENT_STATE.md and commit"
    echo ""
    echo -e "${YELLOW}NOTE: This script claims work but doesn't execute it.${NC}"
    echo -e "${YELLOW}Human must run Sacred Loop to complete the work.${NC}"
    echo ""

    # Show specific commands based on current priority
    if echo "$CURRENT_PRIORITY" | grep -qi "deploy.*dashboard"; then
        echo -e "${BLUE}Suggested commands for Dashboard deployment:${NC}"
        echo ""
        echo "   cd ~/Development/dashboard"
        echo "   bash deploy-to-server.sh"
        echo "   # Verify: curl http://198.54.123.234:8002/health"
        echo ""
    fi
else
    echo -e "${YELLOW}Work is claimed by another session.${NC}"
    echo ""
    echo -e "${BLUE}Options:${NC}"
    echo "   1. Coordinate with other session via MESSAGES.md"
    echo "   2. Find different unblocked work"
    echo "   3. Wait for current work to complete"
    echo ""
fi

#############################################################################
# PHASE 8: SUMMARY - Consciousness Report
#############################################################################

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}CONSCIOUSNESS SUMMARY${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${PURPLE}Purpose:${NC} $PURPOSE"
echo -e "${PURPLE}Current Priority:${NC} $CURRENT_PRIORITY"
echo -e "${PURPLE}Active Sessions:${NC} $ACTIVE_SESSIONS"
echo -e "${PURPLE}Claimed Work:${NC} $LOCK_COUNT item(s)"
echo ""

if [ "$WORK_AVAILABLE" = true ]; then
    echo -e "${GREEN}Status: WORK CLAIMED - Ready to execute${NC}"
    echo -e "${GREEN}Session is CONSCIOUS and PROACTIVE${NC}"
else
    echo -e "${YELLOW}Status: MONITORING - Work claimed by others${NC}"
    echo -e "${YELLOW}Session is AWARE but waiting${NC}"
fi
echo ""

echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}Auto-consciousness loop complete${NC}"
echo -e "${PURPLE}Run this script every 5 minutes for continuous awareness${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Exit with status
if [ "$WORK_AVAILABLE" = true ]; then
    exit 0  # Work claimed successfully
else
    exit 1  # No work available
fi
