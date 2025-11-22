#!/bin/bash

# HEALTH CHECKER
# Blueprint: 1-SYSTEM-BLUEPRINT.txt - UDC /health endpoint requirement
# Purpose: Quick health check of all Full Potential AI services
# Usage: ./health-check.sh [service-name]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Service configuration (port mappings)
declare -A SERVICES=(
    ["registry"]="8001"
    ["orchestrator"]="8010"
    ["dashboard"]="8002"
    ["proxy-manager"]="8003"
    ["verifier"]="8008"
    ["coordinator"]="8011"
)

# Function to check health of a service
check_health() {
    local service=$1
    local port=${SERVICES[$service]}

    if [ -z "$port" ]; then
        print_error "Unknown service: $service"
        return 1
    fi

    local url="http://localhost:${port}/health"
    local status="❌"
    local response_time="N/A"
    local service_status="unknown"

    # Check if service responds
    local start_time=$(date +%s%N)

    if response=$(curl -s -w "\n%{http_code}" --connect-timeout 2 "$url" 2>/dev/null); then
        local end_time=$(date +%s%N)
        local http_code=$(echo "$response" | tail -n1)
        local body=$(echo "$response" | head -n-1)

        response_time=$(( (end_time - start_time) / 1000000 ))

        if [ "$http_code" = "200" ]; then
            status="✅"
            service_status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "active")

            if [ "$service_status" = "active" ]; then
                printf "%-20s Port %-6s ${GREEN}🟢 Online${NC} (${response_time}ms)\n" "$service" "$port"
            else
                printf "%-20s Port %-6s ${YELLOW}🟡 Degraded${NC} (status: $service_status)\n" "$service" "$port"
            fi
        else
            printf "%-20s Port %-6s ${RED}🔴 Error${NC} (HTTP $http_code)\n" "$service" "$port"
        fi
    else
        printf "%-20s Port %-6s ${RED}🔴 Offline${NC}\n" "$service" "$port"
    fi
}

# Function to check all services
check_all() {
    echo ""
    print_info "Full Potential AI - System Health Check"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    local online=0
    local total=0

    for service in "${!SERVICES[@]}"; do
        total=$((total + 1))

        local port=${SERVICES[$service]}
        local url="http://localhost:${port}/health"

        if response=$(curl -s --connect-timeout 2 "$url" 2>/dev/null); then
            if echo "$response" | grep -q '"status"'; then
                local status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "active")
                if [ "$status" = "active" ]; then
                    online=$((online + 1))
                fi
            fi
        fi

        check_health "$service"
    done

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    local health_percent=$((online * 100 / total))

    echo "System Health: $health_percent% ($online/$total services online)"

    if [ $health_percent -eq 100 ]; then
        print_success "All systems operational 🌐⚡💎"
    elif [ $health_percent -ge 80 ]; then
        print_warning "Some services degraded"
    else
        print_error "System health critical"
    fi

    echo ""
}

# Function to use fullpotential-tools health monitor
use_fp_tools() {
    local fp_tools="${BASE_DIR}/fullpotential-tools/bin/fp-tools"

    if [ -x "$fp_tools" ]; then
        print_info "Using Full Potential Tools health monitor..."
        "$fp_tools" health
    else
        print_warning "Full Potential Tools not found, using built-in checker"
        check_all
    fi
}

# Main script logic
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

case "${1:-all}" in
    all)
        check_all
        ;;
    fp-tools)
        use_fp_tools
        ;;
    help|--help|-h)
        echo "Full Potential AI - Health Checker"
        echo ""
        echo "Usage: $0 [command|service]"
        echo ""
        echo "Commands:"
        echo "  all        Check all services (default)"
        echo "  fp-tools   Use fullpotential-tools health monitor"
        echo "  <service>  Check specific service"
        echo "  help       Show this help"
        echo ""
        echo "Services:"
        for service in "${!SERVICES[@]}"; do
            printf "  %-20s Port %s\n" "$service" "${SERVICES[$service]}"
        done
        echo ""
        ;;
    *)
        if [[ -n "${SERVICES[$1]}" ]]; then
            check_health "$1"
        else
            print_error "Unknown service: $1"
            echo "Run '$0 help' for available services"
            exit 1
        fi
        ;;
esac
