#!/bin/bash

# UDC API Test Script for Droplet #5 (Dashboard)
# Replace with your actual dashboard URL
ENDPOINT="${DASHBOARD_URL:-http://localhost:3000}"

echo "🧪 Testing UDC API Endpoints for Droplet #5"
echo "Endpoint: $ENDPOINT"
echo "=========================================="

# 1. Health Check (Public)
echo -e "\n✅ 1. GET /health"
curl -X GET "$ENDPOINT/api/health" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

# 2. Capabilities
echo -e "\n✅ 2. GET /capabilities"
curl -X GET "$ENDPOINT/api/capabilities" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

# 3. State
echo -e "\n✅ 3. GET /state"
curl -X GET "$ENDPOINT/api/state" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

# 4. Dependencies
echo -e "\n✅ 4. GET /dependencies"
curl -X GET "$ENDPOINT/api/dependencies" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

# 5. Version
echo -e "\n✅ 5. GET /version"
curl -X GET "$ENDPOINT/api/version" \
  -H "Accept: application/json" \
  -w "\nStatus: %{http_code}\n"

# 6. Receive Message
echo -e "\n✅ 6. POST /message"
curl -X POST "$ENDPOINT/api/message" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "source": "droplet-10",
    "target": "droplet-5",
    "message_type": "command",
    "payload": {
      "command": "test",
      "data": "Hello from test script"
    },
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "trace_id": "'$(uuidgen || echo "test-trace-$(date +%s)")'"
  }' \
  -w "\nStatus: %{http_code}\n"

# 7. Send Message
echo -e "\n✅ 7. POST /send"
curl -X POST "$ENDPOINT/api/send" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "target_droplet_id": "droplet-10",
    "message_type": "query",
    "payload": {
      "query": "status"
    }
  }' \
  -w "\nStatus: %{http_code}\n"

# 8. Reload Config
echo -e "\n✅ 8. POST /reload-config"
curl -X POST "$ENDPOINT/api/reload-config" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "reason": "Test reload from script"
  }' \
  -w "\nStatus: %{http_code}\n"

# 9. Shutdown (commented out for safety)
echo -e "\n⚠️  9. POST /shutdown (SKIPPED - uncomment to test)"
# curl -X POST "$ENDPOINT/api/shutdown" \
#   -H "Content-Type: application/json" \
#   -d '{"reason": "Test shutdown"}' \
#   -w "\nStatus: %{http_code}\n"

# 10. Emergency Stop (commented out for safety)
echo -e "\n⚠️  10. POST /emergency-stop (SKIPPED - uncomment to test)"
# curl -X POST "$ENDPOINT/api/emergency-stop" \
#   -H "Content-Type: application/json" \
#   -d '{"reason": "Test emergency stop"}' \
#   -w "\nStatus: %{http_code}\n"

echo -e "\n=========================================="
echo "✅ UDC API Test Complete"
