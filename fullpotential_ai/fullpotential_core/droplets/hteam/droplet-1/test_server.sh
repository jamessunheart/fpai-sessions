#!/bin/bash
# Quick server testing script for 146.190.114.225

SERVER="http://146.190.114.225:7860"

echo "=========================================="
echo "Testing Full Potential OS API"
echo "Server: $SERVER"
echo "=========================================="
echo ""

# Test 1: Health Check
echo "1️⃣  Health Check:"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$SERVER/health")
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: $HTTP_CODE"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo "❌ Status: $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 2: Chat Endpoint
echo "2️⃣  Chat Endpoint:"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$SERVER/chat" \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"Server deployment test message"}')
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: $HTTP_CODE"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo "❌ Status: $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 3: Chat with User ID
echo "3️⃣  Chat with User ID:"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$SERVER/chat" \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"Test with custom user","user_id":"test_user_123"}')
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: $HTTP_CODE"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo "❌ Status: $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 4: Reflect Endpoint
echo "4️⃣  Reflect Endpoint:"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$SERVER/reflect" \
  -H "Content-Type: application/json" \
  -d '{"summary":"Server test reflection","insights":["System operational"],"decisions":["Continue monitoring"],"user_id":"test_user"}')
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: $HTTP_CODE"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo "❌ Status: $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 5: Intent Endpoint
echo "5️⃣  Intent Endpoint:"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$SERVER/intent" \
  -H "Content-Type: application/json" \
  -d '{"intent":"Verify server deployment","horizon_min":60,"tags":["deployment","testing"],"user_id":"test_user"}')
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: $HTTP_CODE"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo "❌ Status: $HTTP_CODE"
    echo "$BODY"
fi
echo ""

# Test 6: Error Handling
echo "6️⃣  Error Handling (Missing Content):"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$SERVER/chat" \
  -H "Content-Type: application/json" \
  -d '{"role":"user"}')
HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "400" ]; then
    echo "✅ Status: $HTTP_CODE (Expected error)"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
else
    echo "⚠️  Status: $HTTP_CODE (Expected 400)"
    echo "$BODY"
fi
echo ""

echo "=========================================="
echo "Testing Complete!"
echo "=========================================="

