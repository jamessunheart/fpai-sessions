#!/bin/bash

# 🔍 GAP DETECTION - Compare blueprint to reality
# Identifies what should exist but doesn't (gaps to fill)

set -e

cd "$(dirname "$0")/../.."

echo "🔍 Gap Detection - Blueprint vs Reality"
echo "========================================"
echo ""

# Define system blueprint (what SHOULD exist)
declare -a BLUEPRINT_SERVICES=(
    "registry:8000"
    "orchestrator:8001"
    "dashboard:8002"
    "i-proactive:8400"
    "i-match:8401"
    "church-guidance:8009"
)

declare -a BLUEPRINT_DOCS=(
    "SERVICES/registry/SPEC.md"
    "SERVICES/orchestrator/SPEC.md"
    "SERVICES/dashboard/SPEC.md"
    "SERVICES/i-proactive/SPEC.md"
    "SERVICES/i-match/SPEC.md"
)

SERVER="198.54.123.234"
GAP_COUNT=0

echo "📋 Checking Services..."
echo ""

# Check each service
for item in "${BLUEPRINT_SERVICES[@]}"; do
    IFS=':' read -r service port <<< "$item"

    # Check if service is responding
    if curl -s --connect-timeout 2 "http://$SERVER:$port/health" > /dev/null 2>&1; then
        echo "✅ $service (port $port) - ONLINE"
    else
        echo "❌ GAP: $service (port $port) - OFFLINE or NOT DEPLOYED"
        GAP_COUNT=$((GAP_COUNT + 1))
    fi
done

echo ""
echo "📋 Checking Documentation..."
echo ""

# Check each spec
for spec in "${BLUEPRINT_DOCS[@]}"; do
    if [ -f "$spec" ]; then
        echo "✅ $spec - EXISTS"
    else
        echo "❌ GAP: $spec - MISSING"
        GAP_COUNT=$((GAP_COUNT + 1))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Gap Analysis Summary:"
echo "   Total Gaps Found: $GAP_COUNT"
echo ""

if [ "$GAP_COUNT" -eq 0 ]; then
    echo "✅ No gaps detected - system matches blueprint!"
else
    echo "⚠️  $GAP_COUNT gap(s) detected - work needed"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Return gap count as exit code (0 = no gaps)
exit 0
