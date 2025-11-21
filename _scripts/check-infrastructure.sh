#!/bin/bash
# FPAI Infrastructure Status Checker
# Quick health check for all core services

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   FPAI INFRASTRUCTURE STATUS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

check_service() {
    local name=$1
    local port=$2
    local endpoint=${3:-/health}

    printf "%-20s (port %5s): " "$name" "$port"

    if ! lsof -i :$port >/dev/null 2>&1; then
        echo -e "${RED}OFFLINE${NC}"
        return 1
    fi

    # Check health endpoint
    local response=$(curl -s --max-time 2 "http://localhost:$port$endpoint" 2>/dev/null)

    if [ -n "$response" ]; then
        # Try to extract status
        local status=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))" 2>/dev/null || echo "responding")

        if [[ "$status" == "active" ]] || [[ "$status" == "healthy" ]]; then
            echo -e "${GREEN}ONLINE${NC} ($status)"
            return 0
        elif [[ "$status" == "error" ]]; then
            echo -e "${YELLOW}DEGRADED${NC} ($status)"
            return 2
        else
            echo -e "${GREEN}ONLINE${NC}"
            return 0
        fi
    else
        echo -e "${YELLOW}RUNNING${NC} (no health endpoint)"
        return 2
    fi
}

echo -e "${BLUE}TIER 0 - Core Infrastructure:${NC}"
check_service "Registry" 8000 "/health"
check_service "Orchestrator" 8001 "/orchestrator/health"
check_service "SPEC Verifier" 8002 "/health"

echo ""
echo -e "${BLUE}TIER 0.5 - Coordination:${NC}"
check_service "Unified Chat" 8100 "/api/health"
check_service "FPAI Hub" 8010 "/health"

echo ""
echo -e "${BLUE}TIER 1 - Revenue Services:${NC}"
check_service "I MATCH" 8401 "/health"
check_service "AI Marketing" 8700 "/health"
check_service "Treasury Arena" 8205 "/health"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Count status
online=0
offline=0
degraded=0

for port in 8000 8001 8002 8010 8100 8401 8700 8205; do
    if lsof -i :$port >/dev/null 2>&1; then
        ((online++))
    else
        ((offline++))
    fi
done

echo ""
echo -e "Summary: ${GREEN}$online online${NC}, ${RED}$offline offline${NC}"
echo ""

if [ $offline -eq 0 ]; then
    echo -e "${GREEN}✓ All infrastructure services operational${NC}"
elif [ $online -eq 0 ]; then
    echo -e "${RED}✗ No services running - run ./start-infrastructure.sh${NC}"
else
    echo -e "${YELLOW}⚠ Some services offline - check logs in /tmp/${NC}"
fi

echo ""
