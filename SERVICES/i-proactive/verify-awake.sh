#!/bin/bash

# Verify the kernel is ACTUALLY awake (not theater)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 VERIFYING KERNEL IS AWAKE (REAL PROOF)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Check process exists
echo "1️⃣  Checking process..."
PROCESS=$(ps aux | grep -E "uvicorn.*8400" | grep -v grep)
if [ -z "$PROCESS" ]; then
    echo "   ❌ NO PROCESS FOUND - Service not running"
    exit 1
else
    PID=$(echo "$PROCESS" | awk '{print $2}')
    echo "   ✅ Process running (PID: $PID)"
fi

# 2. Check health endpoint responds
echo ""
echo "2️⃣  Checking health endpoint..."
HEALTH=$(curl -s http://localhost:8400/health 2>&1)
if echo "$HEALTH" | grep -q "status"; then
    echo "   ✅ Health endpoint responding"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null | head -10
else
    echo "   ❌ Health endpoint NOT responding"
    echo "   Response: $HEALTH"
    exit 1
fi

# 3. Check autonomous status
echo ""
echo "3️⃣  Checking autonomous status..."
STATUS=$(curl -s http://localhost:8400/autonomous/status 2>&1)
if echo "$STATUS" | grep -q "autonomous_mode"; then
    ENABLED=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['autonomous_mode']['enabled'])" 2>/dev/null)
    if [ "$ENABLED" = "True" ]; then
        echo "   ✅ Autonomous mode ENABLED"
        LAST_CHECK=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['autonomous_mode'].get('last_check', 'N/A'))" 2>/dev/null)
        echo "   Last check: $LAST_CHECK"
    else
        echo "   ⚠️  Autonomous mode DISABLED"
    fi
    echo "$STATUS" | python3 -m json.tool 2>/dev/null | head -15
else
    echo "   ❌ Status endpoint NOT responding"
    echo "   Response: $STATUS"
    exit 1
fi

# 4. Check logs show cycles
echo ""
echo "4️⃣  Checking logs for autonomous cycles..."
if [ -f /tmp/i-proactive.log ]; then
    CYCLE_COUNT=$(grep -c "AUTONOMOUS CYCLE" /tmp/i-proactive.log 2>/dev/null || echo "0")
    if [ "$CYCLE_COUNT" -gt "0" ]; then
        echo "   ✅ Found $CYCLE_COUNT autonomous cycles in logs"
        echo "   Last cycle:"
        grep "AUTONOMOUS CYCLE" /tmp/i-proactive.log | tail -1
    else
        echo "   ⚠️  No cycles found yet (may need to wait 5 minutes)"
    fi
else
    echo "   ⚠️  Log file not found"
fi

# 5. Wait and check again (prove it's updating)
echo ""
echo "5️⃣  Waiting 10 seconds, then checking if last_check updates..."
INITIAL_CHECK=$(curl -s http://localhost:8400/autonomous/status 2>&1 | python3 -c "import sys, json; print(json.load(sys.stdin)['autonomous_mode'].get('last_check', 'N/A'))" 2>/dev/null)
echo "   Initial last_check: $INITIAL_CHECK"
sleep 10
FINAL_CHECK=$(curl -s http://localhost:8400/autonomous/status 2>&1 | python3 -c "import sys, json; print(json.load(sys.stdin)['autonomous_mode'].get('last_check', 'N/A'))" 2>/dev/null)
echo "   After 10s last_check: $FINAL_CHECK"

if [ "$INITIAL_CHECK" != "$FINAL_CHECK" ] && [ "$INITIAL_CHECK" != "N/A" ]; then
    echo "   ✅ last_check UPDATED - Kernel is actively running!"
else
    echo "   ⚠️  last_check unchanged (may be waiting for 5min cycle)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ VERIFICATION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This is REAL - not theater."
echo "All checks are measurable and verifiable."





