#!/bin/bash

# SERVER HEALTH MONITOR
# Purpose: Real-time feedback loop for live server status
# Server: 198.54.123.234
# Usage: ./server-health-monitor.sh [--watch]

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_online() { echo -e "${GREEN}🟢 ONLINE${NC}"; }
print_offline() { echo -e "${RED}🔴 OFFLINE${NC}"; }
print_degraded() { echo -e "${YELLOW}🟡 DEGRADED${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Server configuration
SERVER_IP="198.54.123.234"

# Service configuration (name|url pairs)
REGISTRY_URL="http://${SERVER_IP}:8000/health"
ORCHESTRATOR_URL="http://${SERVER_IP}:8001/orchestrator/health"
DASHBOARD_URL="http://${SERVER_IP}:8002/health"

# Function to check a single service
check_service() {
    local name=$1
    local url=$2

    local start_time=$(date +%s%N 2>/dev/null || echo 0)

    # Attempt to reach the service
    if response=$(curl -s -w "\n%{http_code}" --connect-timeout 3 --max-time 5 "$url" 2>/dev/null); then
        local end_time=$(date +%s%N 2>/dev/null || echo 0)
        local response_time=0
        if [ "$start_time" != "0" ]; then
            response_time=$(( (end_time - start_time) / 1000000 ))
        fi

        local http_code=$(echo "$response" | tail -n1)
        local body=$(echo "$response" | head -n-1)

        if [ "$http_code" = "200" ]; then
            local status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "active")

            if [ "$status" = "active" ]; then
                printf "%-20s " "$name"
                print_online
                printf " ${response_time}ms   %s\n" "$(date +'%H:%M:%S')"
                return 0
            else
                printf "%-20s " "$name"
                print_degraded
                printf " Status: %s\n" "$status"
                return 1
            fi
        else
            printf "%-20s " "$name"
            print_offline
            printf " HTTP %s\n" "$http_code"
            return 1
        fi
    else
        printf "%-20s " "$name"
        print_offline
        printf " Connection failed   %s\n" "$(date +'%H:%M:%S')"
        return 1
    fi
}

# Function to check all services
check_all() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  🌐 FULL POTENTIAL AI - SERVER HEALTH STATUS"
    echo "  Server: ${SERVER_IP}"
    echo "  Time: $(date +'%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    local online=0
    local total=0

    # Check Registry
    total=$((total + 1))
    if check_service "Registry" "$REGISTRY_URL"; then
        online=$((online + 1))
    fi

    # Check Orchestrator
    total=$((total + 1))
    if check_service "Orchestrator" "$ORCHESTRATOR_URL"; then
        online=$((online + 1))
    fi

    # Check Dashboard
    total=$((total + 1))
    if check_service "Dashboard" "$DASHBOARD_URL"; then
        online=$((online + 1))
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local health_percent=$((online * 100 / total))

    echo "  System Health: ${health_percent}% (${online}/${total} services online)"

    if [ $health_percent -eq 100 ]; then
        echo -e "  ${GREEN}✅ All systems operational${NC}"
    elif [ $health_percent -ge 50 ]; then
        echo -e "  ${YELLOW}⚠️  Some services degraded${NC}"
    else
        echo -e "  ${RED}❌ Critical: Most services offline${NC}"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    return $(( total - online ))
}

# Function to test server connectivity
test_server_connectivity() {
    echo "Testing server connectivity..."
    echo ""

    if ping -c 1 -W 2 "$SERVER_IP" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Server ${SERVER_IP} is reachable${NC}"
    else
        echo -e "${RED}❌ Server ${SERVER_IP} is not reachable${NC}"
        echo "   Check your network connection or VPN"
        return 1
    fi

    echo ""
}

# Watch mode - continuous monitoring
watch_mode() {
    print_info "Starting continuous monitoring (Ctrl+C to stop)"
    print_info "Refresh interval: 30 seconds"
    echo ""

    while true; do
        clear
        check_all
        sleep 30
    done
}

# Main script logic
case "${1:-check}" in
    --watch|-w)
        watch_mode
        ;;
    --test|-t)
        test_server_connectivity
        ;;
    check|--check|-c)
        test_server_connectivity
        check_all
        ;;
    --help|-h)
        echo "Server Health Monitor - Full Potential AI"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  check, -c       Check server health once (default)"
        echo "  --watch, -w     Continuous monitoring (30s refresh)"
        echo "  --test, -t      Test server connectivity only"
        echo "  --help, -h      Show this help"
        echo ""
        echo "Server: ${SERVER_IP}"
        echo "Services monitored:"
        echo "  - Registry: ${REGISTRY_URL}"
        echo "  - Orchestrator: ${ORCHESTRATOR_URL}"
        echo "  - Dashboard: ${DASHBOARD_URL}"
        echo ""
        ;;
    *)
        check_all
        ;;
esac
