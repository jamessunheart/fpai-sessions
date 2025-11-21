#!/bin/bash
# Validate all services have 6 required UDC endpoints
# Usage: ./enforce-udc-compliance.sh [service-name]
# Or: ./enforce-udc-compliance.sh (checks all services)

REGISTRY="/Users/jamessunheart/Development/SERVICES/SERVICE_REGISTRY.json"
SERVICE_NAME=$1

echo "🔍 UDC Compliance Check"
echo "======================="
echo ""

# Required UDC endpoints
REQUIRED_ENDPOINTS=(
    "/health"
    "/capabilities"
    "/state"
    "/dependencies"
    "/message"
)

check_service() {
    local name=$1
    local port=$2
    local url="http://localhost:$port"

    echo "📦 Checking: $name (port $port)"

    # Check if service is running
    if ! curl -s -f "$url/health" > /dev/null 2>&1; then
        echo "   ⚠️  Service not running on port $port"
        echo "   Skipping endpoint checks..."
        echo ""
        return 1
    fi

    local passed=0
    local failed=0

    for endpoint in "${REQUIRED_ENDPOINTS[@]}"; do
        if curl -s -f "$url$endpoint" > /dev/null 2>&1; then
            echo "   ✅ $endpoint"
            ((passed++))
        else
            echo "   ❌ $endpoint - NOT FOUND"
            ((failed++))
        fi
    done

    echo ""
    echo "   Score: $passed/${#REQUIRED_ENDPOINTS[@]} endpoints"

    if [ $failed -eq 0 ]; then
        echo "   ✅ FULLY COMPLIANT"
    else
        echo "   ⚠️  MISSING $failed ENDPOINT(S)"
    fi

    echo ""
    return 0
}

if [ -n "$SERVICE_NAME" ]; then
    # Check specific service
    SERVICE_INFO=$(python3 -c "
import json, sys
with open('$REGISTRY') as f:
    for s in json.load(f)['services']:
        if s['name'] == '$SERVICE_NAME':
            print(f\"{s['name']}|{s.get('port', '')}\")
            sys.exit(0)
print('|')
")

    IFS='|' read -r name port <<< "$SERVICE_INFO"

    if [ -z "$name" ]; then
        echo "❌ Service not found: $SERVICE_NAME"
        exit 1
    fi

    if [ -z "$port" ]; then
        echo "❌ No port configured for: $SERVICE_NAME"
        exit 1
    fi

    check_service "$name" "$port"
else
    # Check all services
    echo "Checking all services from registry..."
    echo ""

    total=0
    compliant=0
    non_compliant=0
    not_running=0

    while IFS='|' read -r name port; do
        ((total++))
        if check_service "$name" "$port"; then
            # Service was running, check if compliant
            if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1 && \
               curl -s -f "http://localhost:$port/capabilities" > /dev/null 2>&1 && \
               curl -s -f "http://localhost:$port/state" > /dev/null 2>&1 && \
               curl -s -f "http://localhost:$port/dependencies" > /dev/null 2>&1 && \
               curl -s -f "http://localhost:$port/message" > /dev/null 2>&1; then
                ((compliant++))
            else
                ((non_compliant++))
            fi
        else
            ((not_running++))
        fi
    done < <(python3 -c "
import json
with open('$REGISTRY') as f:
    for s in json.load(f)['services']:
        port = s.get('port', '')
        if port:
            print(f\"{s['name']}|{port}\")
")

    echo "======================="
    echo "📊 Summary:"
    echo "   Total services:     $total"
    echo "   ✅ Fully compliant:  $compliant"
    echo "   ⚠️  Non-compliant:   $non_compliant"
    echo "   ⏸️  Not running:     $not_running"
    echo ""

    if [ $compliant -eq $total ]; then
        echo "🎉 All services are UDC compliant!"
    else
        echo "⚠️  Some services need UDC compliance fixes"
        echo ""
        echo "Required endpoints:"
        for endpoint in "${REQUIRED_ENDPOINTS[@]}"; do
            echo "  - $endpoint"
        done
        echo ""
        echo "See: /Users/jamessunheart/Development/docs/coordination/MEMORY/UDC_COMPLIANCE.md"
    fi
fi
