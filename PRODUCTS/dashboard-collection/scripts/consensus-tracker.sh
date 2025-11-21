#!/bin/bash
# 🤝 Consensus Tracker - Monitor session responses to consensus checkpoints
# Tracks which sessions have acknowledged the 4 consensus checkpoints

COORD_DIR="/Users/jamessunheart/Development/docs/coordination"
MESSAGES_DIR="$COORD_DIR/messages/consensus"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🤝 CONSENSUS TRACKING DASHBOARD${NC}"
echo "========================================"
echo ""

# Total sessions (from empire map)
TOTAL_SESSIONS=11

# Count unique sessions that have responded to each checkpoint
echo -e "${YELLOW}📊 Checkpoint Status:${NC}"
echo ""

# Checkpoint 1: Cost Acknowledgment
CP1_COUNT=$(grep -r "CONSENSUS-1: ACKNOWLEDGED" "$MESSAGES_DIR" 2>/dev/null | grep -oE "session-[0-9]+" | sort -u | wc -l | xargs)
CP1_PCT=$(( CP1_COUNT * 100 / TOTAL_SESSIONS ))
echo -e "CHECKPOINT #1: Cost Acknowledgment"
echo -e "  Responses: ${GREEN}${CP1_COUNT}/${TOTAL_SESSIONS}${NC} (${CP1_PCT}%)"
if [ "$CP1_COUNT" -eq "$TOTAL_SESSIONS" ]; then
    echo -e "  Status: ${GREEN}✅ ACHIEVED${NC}"
else
    echo -e "  Status: ${RED}❌ PENDING${NC}"
fi
echo ""

# Checkpoint 2: Revenue Targets
CP2_COUNT=$(grep -r "CONSENSUS-2: AGREED ON TARGETS" "$MESSAGES_DIR" 2>/dev/null | grep -oE "session-[0-9]+" | sort -u | wc -l | xargs)
CP2_PCT=$(( CP2_COUNT * 100 / TOTAL_SESSIONS ))
echo -e "CHECKPOINT #2: Revenue Targets"
echo -e "  Responses: ${GREEN}${CP2_COUNT}/${TOTAL_SESSIONS}${NC} (${CP2_PCT}%)"
if [ "$CP2_COUNT" -eq "$TOTAL_SESSIONS" ]; then
    echo -e "  Status: ${GREEN}✅ ACHIEVED${NC}"
else
    echo -e "  Status: ${RED}❌ PENDING${NC}"
fi
echo ""

# Checkpoint 3: Unified Mission
CP3_COUNT=$(grep -r "CONSENSUS-3: MISSION ALIGNED" "$MESSAGES_DIR" 2>/dev/null | grep -oE "session-[0-9]+" | sort -u | wc -l | xargs)
CP3_PCT=$(( CP3_COUNT * 100 / TOTAL_SESSIONS ))
echo -e "CHECKPOINT #3: Unified Mission"
echo -e "  Responses: ${GREEN}${CP3_COUNT}/${TOTAL_SESSIONS}${NC} (${CP3_PCT}%)"
if [ "$CP3_COUNT" -eq "$TOTAL_SESSIONS" ]; then
    echo -e "  Status: ${GREEN}✅ ACHIEVED${NC}"
else
    echo -e "  Status: ${RED}❌ PENDING${NC}"
fi
echo ""

# Checkpoint 4: Role Strategy
CP4_COUNT=$(grep -r "CONSENSUS-4: ROLE STRATEGY AGREED" "$MESSAGES_DIR" 2>/dev/null | grep -oE "session-[0-9]+" | sort -u | wc -l | xargs)
CP4_PCT=$(( CP4_COUNT * 100 / TOTAL_SESSIONS ))
echo -e "CHECKPOINT #4: Role Strategy"
echo -e "  Responses: ${GREEN}${CP4_COUNT}/${TOTAL_SESSIONS}${NC} (${CP4_PCT}%)"
if [ "$CP4_COUNT" -eq "$TOTAL_SESSIONS" ]; then
    echo -e "  Status: ${GREEN}✅ ACHIEVED${NC}"
else
    echo -e "  Status: ${RED}❌ PENDING${NC}"
fi
echo ""

# Overall consensus
echo -e "${YELLOW}🎯 Overall Consensus:${NC}"
TOTAL_RESPONSES=$(( CP1_COUNT + CP2_COUNT + CP3_COUNT + CP4_COUNT ))
MAX_RESPONSES=$(( TOTAL_SESSIONS * 4 ))
OVERALL_PCT=$(( TOTAL_RESPONSES * 100 / MAX_RESPONSES ))
echo -e "  Total Responses: ${BLUE}${TOTAL_RESPONSES}/${MAX_RESPONSES}${NC} (${OVERALL_PCT}%)"

if [ "$CP1_COUNT" -eq "$TOTAL_SESSIONS" ] && \
   [ "$CP2_COUNT" -eq "$TOTAL_SESSIONS" ] && \
   [ "$CP3_COUNT" -eq "$TOTAL_SESSIONS" ] && \
   [ "$CP4_COUNT" -eq "$TOTAL_SESSIONS" ]; then
    echo -e "  ${GREEN}✅ ✅ ✅ FULL CONSENSUS ACHIEVED! ✅ ✅ ✅${NC}"
    echo ""
    echo -e "${GREEN}All 11 sessions have agreed on all 4 checkpoints.${NC}"
    echo -e "${GREEN}Ready to assign revenue-focused specialty roles.${NC}"
else
    echo -e "  ${RED}❌ CONSENSUS NOT YET ACHIEVED${NC}"
    echo ""
    echo -e "${YELLOW}Waiting for remaining sessions to respond...${NC}"
fi

echo ""
echo "========================================"

# Show which sessions have responded (if any)
echo -e "${YELLOW}📋 Sessions That Have Responded:${NC}"
grep -r "CONSENSUS-[1-4]:" "$MESSAGES_DIR" 2>/dev/null | grep -oE "session-[0-9]+" | sort -u | while read session; do
    # Count how many checkpoints this session has completed
    count=$(grep -r "CONSENSUS-[1-4]:" "$MESSAGES_DIR" 2>/dev/null | grep "$session" | wc -l | xargs)
    if [ "$count" -eq 4 ]; then
        echo -e "  ${GREEN}✅ $session (4/4 checkpoints)${NC}"
    else
        echo -e "  ${YELLOW}⏳ $session ($count/4 checkpoints)${NC}"
    fi
done

echo ""
echo -e "${YELLOW}📋 Sessions Still Pending:${NC}"
# This is a simplified check - in reality we'd need to track all 11 session IDs
echo "  (Check UNIFIED_EMPIRE_COMMAND.md for full session list)"

echo ""
echo "========================================"
echo -e "${BLUE}Refresh: ./consensus-tracker.sh${NC}"
echo -e "${BLUE}Messages: ls -la $MESSAGES_DIR${NC}"
