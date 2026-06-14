#!/bin/bash
# Quick test script for Chief of Staff

echo "🧪 Testing Chief of Staff Signal Processing"
echo ""

# Test 1: Urgent signal (should send Telegram)
echo "1️⃣  Sending URGENT signal (should alert via Telegram)..."
curl -s -X POST http://localhost:8107/signal \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "test",
    "type": "error",
    "title": "Test: Critical Error Detected",
    "description": "This is a test urgent signal - should appear in Telegram",
    "data": {"test": true},
    "urgency_hint": "urgent"
  }' | python3 -m json.tool
echo ""

# Test 2: Important signal (daily digest only)
echo "2️⃣  Sending IMPORTANT signal (digest only, no immediate alert)..."
curl -s -X POST http://localhost:8107/signal \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "test",
    "type": "metric",
    "title": "Zen Village: Booking conversion rate improved",
    "description": "Conversion rate up 5% this week - good trend",
    "data": {"conversion_rate": 0.15}
  }' | python3 -m json.tool
echo ""

# Test 3: Context signal (filtered out)
echo "3️⃣  Sending CONTEXT signal (filtered out, logged only)..."
curl -s -X POST http://localhost:8107/signal \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "test",
    "type": "event",
    "title": "System: Database backup completed",
    "description": "Routine backup completed successfully",
    "data": {"auto_handled": true}
  }' | python3 -m json.tool
echo ""

# Show current status
echo "📊 Current Status:"
curl -s http://localhost:8107/status | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'  🔴 Urgent: {d[\"urgent_count\"]}'); print(f'  🟡 Important: {d[\"important_count\"]}'); print(f'  🟢 Auto-handled: {d[\"auto_handled_count\"]}'); print(f'  📊 Context: {d[\"context_count\"]}')"
echo ""

echo "✅ Test complete!"
echo ""
echo "📱 Check your Telegram (@sunheartbrain_bot) for the urgent alert"
echo "🌐 Dashboard: http://localhost:8107/dashboard"
echo "📋 API Docs: http://localhost:8107/docs"
