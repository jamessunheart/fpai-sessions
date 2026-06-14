#!/bin/bash
# Service Health Check Dashboard
# Optimized by: Atlas - Session #1
# Purpose: Instant visibility into all service statuses

echo "🏥 Full Potential AI - Service Health Dashboard"
echo "$(date)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local name=$1
    local port=$2
    local endpoint=$3
    local tier=$4

    # Check if port is listening
    if ! lsof -i :$port >/dev/null 2>&1; then
        echo -e "[$tier] ${RED}●${NC} $name (port $port) - OFFLINE"
        return
    fi

    # Check health endpoint
    if curl -s -f "http://localhost:$port$endpoint" > /dev/null 2>&1; then
        local status=$(curl -s "http://localhost:$port$endpoint" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))" 2>/dev/null)
        if [ "$status" = "active" ] || [ "$status" = "healthy" ]; then
            echo -e "[$tier] ${GREEN}●${NC} $name (port $port) - HEALTHY"
        else
            echo -e "[$tier] ${YELLOW}●${NC} $name (port $port) - DEGRADED ($status)"
        fi
    else
        echo -e "[$tier] ${YELLOW}●${NC} $name (port $port) - RUNNING (no health check)"
    fi
}

echo "TIER 0: Infrastructure Spine"
echo "─────────────────────────────────────────"
check_service "Registry" 8000 "/health" "T0"
check_service "Orchestrator" 8001 "/orchestrator/health" "T0"
check_service "Credentials Manager" 8025 "/health" "T0"

echo ""
echo "TIER 1: Sacred Loop"
echo "─────────────────────────────────────────"
check_service "Autonomous Executor" 8402 "/health" "T1"

echo ""
echo "TIER 2+: Application Services"
echo "─────────────────────────────────────────"
check_service "I MATCH" 8401 "/health" "T2"
check_service "FPAI Hub" 8010 "/health" "T2"
check_service "Unified Chat" 8100 "/health" "T2"

echo ""
echo "Other Active Ports"
echo "─────────────────────────────────────────"
check_service "Port 8002" 8002 "/health" "??"
check_service "Port 8009" 8009 "/health" "??"
check_service "Port 8026" 8026 "/health" "??"
check_service "Port 8035" 8035 "/health" "??"
check_service "Port 8050" 8050 "/health" "??"
check_service "Port 8052" 8052 "/health" "??"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Registry Droplets:"
echo ""
curl -s http://localhost:8000/droplets 2>/dev/null | python3 -m json.tool 2>/dev/null | head -20 || echo "  ❌ Registry unavailable"
echo ""
