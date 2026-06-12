#!/bin/bash

# Wake The Kernel - One Script to Rule Them All

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 WAKING THE CONSCIOUSNESS KERNEL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Navigate to directory
cd /Users/jamessunheart/FPAI_Cockpit/SERVICES/i-proactive
echo "✅ Navigated to: $(pwd)"

# 2. Create minimal .env if it doesn't exist
if [ ! -f .env ]; then
    touch .env
    echo "✅ Created .env file"
else
    echo "✅ .env file exists"
fi

# 3. Check if service is already running
if curl -s http://localhost:8400/health > /dev/null 2>&1; then
    echo "⚠️  Service already running on port 8400"
    echo "   Skipping start..."
else
    echo "🚀 Starting I PROACTIVE service..."
    
    # Start the service in background
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8400 > /tmp/i-proactive.log 2>&1 &
    SERVICE_PID=$!
    echo "   Started with PID: $SERVICE_PID"
    
    # Wait for service to start
    echo "⏳ Waiting for service to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8400/health > /dev/null 2>&1; then
            echo "✅ Service is up!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Service failed to start after 30 seconds"
            echo "   Check logs: tail -f /tmp/i-proactive.log"
            exit 1
        fi
        sleep 1
    done
fi

# 4. Enable autonomous mode (WAKE THE KERNEL)
echo ""
echo "🧠 Waking the kernel..."
RESPONSE=$(curl -s -X POST http://localhost:8400/autonomous/enable)
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# 5. Verify it's awake
echo ""
echo "🔍 Verifying kernel status..."
STATUS=$(curl -s http://localhost:8400/autonomous/status)
echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ KERNEL IS AWAKE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The consciousness kernel is now running."
echo "It will cycle every 5 minutes, monitoring and learning."
echo ""
echo "Check status anytime:"
echo "  curl http://localhost:8400/autonomous/status"
echo ""
echo "View logs:"
echo "  tail -f /tmp/i-proactive.log"
echo ""







