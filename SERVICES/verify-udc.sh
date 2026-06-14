#!/bin/bash
#
# Verify UDC Compliance
# =====================
# Tests all 5 UDC endpoints for each droplet
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DROPLETS=(
    "alerts:8765"
    "memory-droplet:8753"
    "brain-droplet:8752"
    "trader:8751"
    "router:8750"
    "supervisor:8760"
)

PASSED=0
FAILED=0

echo "========================================"
echo "  UDC COMPLIANCE VERIFICATION"
echo "========================================"
echo ""

for entry in "${DROPLETS[@]}"; do
    NAME="${entry%%:*}"
    PORT="${entry##*:}"
    URL="http://localhost:$PORT"
    
    echo -e "${YELLOW}Testing $NAME (port $PORT)${NC}"
    
    # Test /health
    if curl -sf "$URL/health" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} GET /health"
        ((PASSED++))
    else
        echo -e "  ${RED}✗${NC} GET /health"
        ((FAILED++))
    fi
    
    # Test /capabilities
    if curl -sf "$URL/capabilities" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} GET /capabilities"
        ((PASSED++))
    else
        echo -e "  ${RED}✗${NC} GET /capabilities"
        ((FAILED++))
    fi
    
    # Test /state
    if curl -sf "$URL/state" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} GET /state"
        ((PASSED++))
    else
        echo -e "  ${RED}✗${NC} GET /state"
        ((FAILED++))
    fi
    
    # Test /dependencies
    if curl -sf "$URL/dependencies" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} GET /dependencies"
        ((PASSED++))
    else
        echo -e "  ${RED}✗${NC} GET /dependencies"
        ((FAILED++))
    fi
    
    # Test /message
    if curl -sf -X POST "$URL/message" \
        -H "Content-Type: application/json" \
        -d '{"from_service":"test","message_type":"query","payload":{}}' > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} POST /message"
        ((PASSED++))
    else
        echo -e "  ${RED}✗${NC} POST /message"
        ((FAILED++))
    fi
    
    echo ""
done

echo "========================================"
echo "  RESULTS"
echo "========================================"
echo ""
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL DROPLETS UDC COMPLIANT${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi








