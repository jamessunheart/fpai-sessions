#!/bin/bash

# Chief of Staff - Test Script
# Tests all signal categories and features

set -e

echo "🧪 Chief of Staff Test Suite"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if services are running
echo "📡 Checking services..."

if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Alerts service is running"
else
    echo -e "${RED}✗${NC} Alerts service is NOT running"
    echo "   Start it with: cd ../alerts && python3 -m app.main"
    exit 1
fi

if curl -s http://localhost:8107/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Chief of Staff is running"
else
    echo -e "${RED}✗${NC} Chief of Staff is NOT running"
    echo "   Start it with: python3 -m app.main"
    exit 1
fi

echo ""
echo "=============================="
echo ""

# Test 1: Urgent Signal (Revenue Impact)
echo -e "${RED}🔴 Test 1: URGENT Signal${NC}"
echo "Sending: Booking conversion drop..."

curl -s -X POST http://localhost:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "zen-village-booking",
    "type": "alert",
    "title": "Booking conversion drop detected",
    "description": "Conversions down 30% in last hour - potential booking flow issue",
    "data": {
      "revenue_change": -0.30,
      "user_facing": true,
      "impact": "Lost ~$500 potential bookings",
      "quick_actions": [
        "Check booking form for errors",
        "Verify payment processor status",
        "Review recent site changes"
      ]
    }
  }' | jq -r '"✓ Categorized as: \(.category) | Action: \(.action) | \(.message)"'

echo -e "${YELLOW}→ Check your Telegram - you should have an urgent alert!${NC}"
echo ""

sleep 2

# Test 2: Important Signal (Needs Attention)
echo -e "${YELLOW}🟡 Test 2: IMPORTANT Signal${NC}"
echo "Sending: API usage spike..."

curl -s -X POST http://localhost:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "fp-index",
    "type": "metric",
    "title": "Chat API usage increased 45%",
    "description": "Significant uptick in chat API calls - may need scaling soon",
    "data": {
      "usage_change": 0.45,
      "current_rate": "1200 req/min"
    }
  }' | jq -r '"✓ Categorized as: \(.category) | Action: \(.action) | \(.message)"'

echo ""

sleep 1

# Test 3: Another Important Signal
echo "Sending: Partnership inquiry..."

curl -s -X POST http://localhost:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "email-intake",
    "type": "event",
    "title": "Partnership inquiry from wellness center",
    "description": "Potential collaboration opportunity - retreat space in Sedona",
    "data": {
      "requires_decision": true,
      "timeline": "2 weeks to respond"
    }
  }' | jq -r '"✓ Categorized as: \(.category) | Action: \(.action) | \(.message)"'

echo ""

sleep 1

# Test 4: Auto-Handled Signal
echo -e "${GREEN}🟢 Test 3: AUTO-HANDLED Signal${NC}"
echo "Sending: Auto-restart event..."

curl -s -X POST http://localhost:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "nginx",
    "type": "event",
    "title": "Auto-restarted nginx due to memory limit",
    "description": "Service automatically recovered from memory threshold",
    "data": {
      "auto_handled": true,
      "recovery_time": "2.3s"
    }
  }' | jq -r '"✓ Categorized as: \(.category) | Action: \(.action) | \(.message)"'

echo ""

sleep 1

# Test 5: Context Signal (Filtered Out)
echo -e "${BLUE}📊 Test 4: CONTEXT Signal${NC}"
echo "Sending: Background metric (not relevant to 30-day goal)..."

curl -s -X POST http://localhost:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "analytics",
    "type": "metric",
    "title": "Database backup completed",
    "description": "Nightly backup finished successfully",
    "data": {
      "size_gb": 12.4,
      "duration_min": 8
    }
  }' | jq -r '"✓ Categorized as: \(.category) | Action: \(.action) | \(.message)"'

echo ""

sleep 1

# Test 6: Multiple Auto-Handled (for pattern detection)
echo -e "${GREEN}🟢 Test 5: Pattern Detection${NC}"
echo "Sending multiple similar events (for automation suggestions)..."

for i in {1..4}; do
  curl -s -X POST http://localhost:8107/signal \
    -H "Content-Type: application/json" \
    -d '{
      "source": "fp-index",
      "type": "event",
      "title": "Auto-scaled memory due to load",
      "description": "Automatically increased memory allocation",
      "data": {"auto_handled": true}
    }' > /dev/null
  echo "  ✓ Event $i/4 sent"
  sleep 0.5
done

echo ""

# Check Status
echo "=============================="
echo ""
echo "📊 Current System Status"
echo "------------------------"

curl -s http://localhost:8107/status | jq '{
  urgent: .urgent_count,
  important: .important_count,
  auto_handled: .auto_handled_count,
  active_issues: (.active_issues | length)
}'

echo ""

# Check Urgent Items
echo "🔴 Current Urgent Items"
echo "------------------------"

curl -s http://localhost:8107/urgent | jq -r '.items[] | "• \(.title)"'

echo ""

# Check Automation Suggestions
echo "🤖 Automation Suggestions"
echo "------------------------"

curl -s http://localhost:8107/automation-suggestions | jq -r '.suggestions[] | "• \(.suggestion) (confidence: \(.confidence * 100)%)"'

echo ""

# Generate and Send Digest
echo "=============================="
echo ""
echo "📨 Sending Daily Digest"
echo "------------------------"

response=$(curl -s -X POST http://localhost:8107/digest/send)
echo "$response" | jq -r '"✓ Digest sent at: \(.sent_at)"'

echo ""
echo -e "${YELLOW}→ Check your Telegram for the full daily briefing!${NC}"

echo ""
echo "=============================="
echo ""
echo "✅ Test Suite Complete!"
echo ""
echo "Next steps:"
echo "  1. Check your Telegram messages"
echo "  2. Open dashboard: http://localhost:8107/dashboard"
echo "  3. View API docs: http://localhost:8107/docs"
echo ""
echo "To integrate with your services:"
echo "  curl -X POST http://localhost:8107/signal \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"source\": \"your-service\", \"type\": \"alert\", \"title\": \"...\", \"description\": \"...\"}'"
echo ""
