#!/bin/bash
# Test script for Full Potential OS API endpoints

BASE_URL="http://localhost:7860"

echo "=========================================="
echo "Testing Full Potential OS API Endpoints"
echo "=========================================="
echo ""

# Test 1: Health Check
echo "1. Testing /health endpoint..."
curl -s -X GET "$BASE_URL/health" | jq .
echo ""
echo "---"
echo ""

# Test 2: Chat endpoint (basic)
echo "2. Testing /chat endpoint (basic)..."
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"Hello, this is a test message"}' | jq .
echo ""
echo "---"
echo ""

# Test 3: Chat endpoint (with user_id)
echo "3. Testing /chat endpoint (with user_id)..."
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"Test with custom user ID","user_id":"test_user_123"}' | jq .
echo ""
echo "---"
echo ""

# Test 4: Chat endpoint (assistant role)
echo "4. Testing /chat endpoint (assistant role)..."
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"role":"assistant","content":"This is an assistant response","user_id":"test_user_123"}' | jq .
echo ""
echo "---"
echo ""

# Test 5: Reflect endpoint
echo "5. Testing /reflect endpoint..."
curl -s -X POST "$BASE_URL/reflect" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Test reflection summary",
    "insights": ["Insight 1", "Insight 2"],
    "decisions": ["Decision A", "Decision B"],
    "user_id": "test_user_123"
  }' | jq .
echo ""
echo "---"
echo ""

# Test 6: Intent endpoint
echo "6. Testing /intent endpoint..."
curl -s -X POST "$BASE_URL/intent" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Complete project documentation",
    "horizon_min": 120,
    "tags": ["work", "documentation"],
    "user_id": "test_user_123"
  }' | jq .
echo ""
echo "---"
echo ""

# Test 7: Error handling - missing content
echo "7. Testing error handling (missing content)..."
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"role":"user"}' | jq .
echo ""
echo "---"
echo ""

echo "=========================================="
echo "All tests completed!"
echo "=========================================="

