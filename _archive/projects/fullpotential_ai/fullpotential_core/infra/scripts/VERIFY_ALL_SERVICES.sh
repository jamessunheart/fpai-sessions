#!/bin/bash

# Sacred Loop Step 5: Automated Verification
# Uses Verifier Droplet to validate I PROACTIVE and I MATCH

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 SACRED LOOP - AUTOMATED VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Using Verifier Droplet (Step 5 of Sacred Loop) to validate:"
echo "  • I PROACTIVE (Droplet #20)"
echo "  • I MATCH (Droplet #21)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Verifier is running
echo "🔍 Checking if Verifier is running..."

if ! curl -s http://localhost:8200/health > /dev/null 2>&1; then
    echo "⚠️  Verifier not running. Starting it now..."
    echo ""

    cd /Users/jamessunheart/Development/agents/services/verifier

    # Install dependencies if needed
    if [ ! -d ".venv" ]; then
        echo "📦 Installing Verifier dependencies..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -q -r requirements.txt
    else
        source .venv/bin/activate
    fi

    # Start Verifier in background
    echo "🚀 Starting Verifier service..."
    uvicorn app.main:app --port 8200 > /tmp/verifier.log 2>&1 &
    VERIFIER_PID=$!

    # Wait for it to start
    echo "⏳ Waiting for Verifier to start..."
    for i in {1..10}; do
        if curl -s http://localhost:8200/health > /dev/null 2>&1; then
            echo "✅ Verifier started successfully (PID: $VERIFIER_PID)"
            break
        fi
        sleep 1
    done

    if ! curl -s http://localhost:8200/health > /dev/null 2>&1; then
        echo "❌ Failed to start Verifier"
        cat /tmp/verifier.log
        exit 1
    fi
else
    echo "✅ Verifier already running"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 VERIFYING I PROACTIVE (Droplet #20)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Submit I PROACTIVE for verification
echo "📤 Submitting I PROACTIVE to Verifier..."

RESPONSE=$(curl -s -X POST http://localhost:8200/verify \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_path": "/Users/jamessunheart/Development/agents/services/i-proactive",
    "droplet_name": "i-proactive",
    "quick_mode": false
  }')

JOB_ID_1=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])" 2>/dev/null || echo "")

if [ -z "$JOB_ID_1" ]; then
    echo "❌ Failed to submit I PROACTIVE"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Verification job created: $JOB_ID_1"
echo "⏳ Running verification (this takes 3-5 minutes)..."
echo ""

# Poll for completion
for i in {1..60}; do
    STATUS_RESPONSE=$(curl -s http://localhost:8200/verify/$JOB_ID_1)
    STATUS=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")

    if [ "$STATUS" = "completed" ]; then
        echo "✅ I PROACTIVE verification completed!"
        echo ""

        # Get summary
        DECISION=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('summary', {}).get('decision', 'unknown'))" 2>/dev/null || echo "unknown")
        PASSED=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('summary', {}).get('phases_passed', 0))" 2>/dev/null || echo "0")
        TOTAL=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('summary', {}).get('total_phases', 6))" 2>/dev/null || echo "6")

        echo "  Decision: $DECISION"
        echo "  Phases Passed: $PASSED/$TOTAL"
        echo ""

        # Get full report
        echo "📊 Full Report:"
        curl -s http://localhost:8200/verify/$JOB_ID_1/report | python3 -m json.tool

        break
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ I PROACTIVE verification failed"
        echo ""
        echo "Error details:"
        echo $STATUS_RESPONSE | python3 -m json.tool
        break
    else
        # Show progress
        printf "."
        sleep 3
    fi
done

echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 VERIFYING I MATCH (Droplet #21)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Submit I MATCH for verification
echo "📤 Submitting I MATCH to Verifier..."

RESPONSE=$(curl -s -X POST http://localhost:8200/verify \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_path": "/Users/jamessunheart/Development/agents/services/i-match",
    "droplet_name": "i-match",
    "quick_mode": false
  }')

JOB_ID_2=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])" 2>/dev/null || echo "")

if [ -z "$JOB_ID_2" ]; then
    echo "❌ Failed to submit I MATCH"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Verification job created: $JOB_ID_2"
echo "⏳ Running verification (this takes 3-5 minutes)..."
echo ""

# Poll for completion
for i in {1..60}; do
    STATUS_RESPONSE=$(curl -s http://localhost:8200/verify/$JOB_ID_2)
    STATUS=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")

    if [ "$STATUS" = "completed" ]; then
        echo "✅ I MATCH verification completed!"
        echo ""

        # Get summary
        DECISION=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('summary', {}).get('decision', 'unknown'))" 2>/dev/null || echo "unknown")
        PASSED=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('summary', {}).get('phases_passed', 0))" 2>/dev/null || echo "0")
        TOTAL=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('summary', {}).get('total_phases', 6))" 2>/dev/null || echo "6")

        echo "  Decision: $DECISION"
        echo "  Phases Passed: $PASSED/$TOTAL"
        echo ""

        # Get full report
        echo "📊 Full Report:"
        curl -s http://localhost:8200/verify/$JOB_ID_2/report | python3 -m json.tool

        break
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ I MATCH verification failed"
        echo ""
        echo "Error details:"
        echo $STATUS_RESPONSE | python3 -m json.tool
        break
    else
        # Show progress
        printf "."
        sleep 3
    fi
done

echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 VERIFICATION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "View detailed reports:"
echo "  I PROACTIVE: curl http://localhost:8200/verify/$JOB_ID_1/report | python3 -m json.tool"
echo "  I MATCH: curl http://localhost:8200/verify/$JOB_ID_2/report | python3 -m json.tool"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
