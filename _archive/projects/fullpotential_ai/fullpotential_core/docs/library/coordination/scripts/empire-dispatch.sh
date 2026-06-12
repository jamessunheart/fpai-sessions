#!/bin/bash
# 🏛️ Empire Dispatch - Unified Command for All Sessions
# Coordinates all Claude sessions for FPAI Empire operations

COORD_DIR="/Users/jamessunheart/Development/docs/coordination"
SCRIPTS_DIR="$COORD_DIR/scripts"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🏛️ FPAI EMPIRE - UNIFIED COMMAND DISPATCH${NC}"
echo "========================================"
echo ""

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  deploy <mission-id>     - Deploy a mission to session(s)"
    echo "  status                  - Get unified empire status"
    echo "  broadcast <message>     - Send message to all sessions"
    echo "  assign <session> <role> - Assign role to specific session"
    echo "  metrics                 - Get empire performance metrics"
    echo "  agents                  - Get all agents status"
    echo "  treasury                - Get treasury status"
    echo ""
    exit 1
fi

COMMAND=$1
shift
TARGET=$1
if [ -n "$TARGET" ]; then shift; fi

case $COMMAND in
    deploy)
        echo -e "${GREEN}📦 Deploying Mission: $TARGET${NC}"
        echo ""

        # Read mission from UNIFIED_EMPIRE_COMMAND.md
        mission_info=$(grep -A 10 "MISSION.*$TARGET" "$COORD_DIR/UNIFIED_EMPIRE_COMMAND.md" | head -15)

        if [ -z "$mission_info" ]; then
            echo -e "${RED}❌ Mission $TARGET not found${NC}"
            exit 1
        fi

        echo "$mission_info"
        echo ""

        # Broadcast mission deployment
        $SCRIPTS_DIR/session-send-message.sh "coordination" \
            "Mission $TARGET Deployed" \
            "Mission $TARGET is now active. See UNIFIED_EMPIRE_COMMAND.md for details. Claim with: session-claim.sh mission-$TARGET"

        echo -e "${GREEN}✅ Mission deployed to all sessions${NC}"
        ;;

    status)
        echo -e "${BLUE}📊 UNIFIED EMPIRE STATUS${NC}"
        echo ""

        # Session status
        echo -e "${YELLOW}Active Sessions:${NC}"
        $SCRIPTS_DIR/session-status.sh 2>/dev/null | grep -E "(session-|Status:|Current Work:)" | head -40
        echo ""

        # Empire metrics
        echo -e "${YELLOW}Empire Metrics:${NC}"
        curl -s http://localhost:8010/api/analytics/empire-metrics 2>/dev/null | python3 -m json.tool | head -30 || \
        curl -s http://198.54.123.234:8040/api/analytics/empire-metrics 2>/dev/null | python3 -m json.tool | head -30 || \
        echo "Empire metrics unavailable"
        ;;

    broadcast)
        MESSAGE="$TARGET $@"
        echo -e "${GREEN}📢 Broadcasting to all sessions:${NC}"
        echo "\"$MESSAGE\""
        echo ""

        $SCRIPTS_DIR/session-send-message.sh "coordination" \
            "Empire Broadcast" \
            "$MESSAGE"

        echo -e "${GREEN}✅ Broadcast sent${NC}"
        ;;

    assign)
        SESSION=$TARGET
        ROLE="$@"
        echo -e "${GREEN}👤 Assigning Role:${NC}"
        echo "Session: $SESSION"
        echo "Role: $ROLE"
        echo ""

        $SCRIPTS_DIR/session-send-message.sh "coordination" \
            "Role Assignment: $SESSION" \
            "Session $SESSION has been assigned role: $ROLE. See UNIFIED_EMPIRE_COMMAND.md for responsibilities."

        echo -e "${GREEN}✅ Role assigned${NC}"
        ;;

    metrics)
        echo -e "${BLUE}📈 EMPIRE PERFORMANCE METRICS${NC}"
        echo ""

        # Try local first, then remote
        metrics=$(curl -s http://localhost:8010/api/analytics/empire-metrics 2>/dev/null || \
                 curl -s http://198.54.123.234:8040/api/analytics/empire-metrics 2>/dev/null)

        if [ -n "$metrics" ]; then
            echo "$metrics" | python3 -m json.tool
        else
            echo -e "${RED}❌ Unable to fetch metrics${NC}"
            echo "Ensure FPAI Hub is running"
        fi
        ;;

    agents)
        echo -e "${BLUE}🤖 AUTONOMOUS AGENTS STATUS${NC}"
        echo ""

        agents=$(curl -s http://localhost:8010/api/agents/status 2>/dev/null || \
                curl -s http://198.54.123.234:8040/api/agents/status 2>/dev/null)

        if [ -n "$agents" ]; then
            echo "$agents" | python3 -m json.tool
        else
            echo -e "${RED}❌ Unable to fetch agent status${NC}"
            echo "Ensure FPAI Hub is running and agents are deployed"
        fi
        ;;

    treasury)
        echo -e "${BLUE}💰 TREASURY STATUS${NC}"
        echo ""

        treasury=$(curl -s http://localhost:8010/api/treasury/status 2>/dev/null || \
                  curl -s http://198.54.123.234:8040/api/treasury/status 2>/dev/null)

        if [ -n "$treasury" ]; then
            echo "$treasury" | python3 -m json.tool
        else
            echo -e "${RED}❌ Unable to fetch treasury status${NC}"
        fi
        ;;

    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo "Run without arguments to see usage"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo -e "${BLUE}Empire Dispatch Complete${NC}"
