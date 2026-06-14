#!/bin/bash
# =============================================================================
# DEPLOY I-MATCH FIX TO PRODUCTION
# =============================================================================
# This deploys the fixed matching_engine.py that uses AI Brain instead of
# broken localhost Ollama + missing Anthropic key
#
# Usage: ./deploy-i-match-fix.sh
# Requires: SSH access to 198.54.123.234

set -e

SERVER="198.54.123.234"
SERVICE_DIR="/opt/fpai/services/i-match"
LOCAL_FILE="/Users/jamessunheart/FPAI_Cockpit/SERVICES/i-match/app/matching_engine.py"

echo "🚀 Deploying I-MATCH fix to production..."
echo ""

# Check if file exists
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Error: $LOCAL_FILE not found"
    exit 1
fi

echo "📁 Copying fixed matching_engine.py to server..."
scp "$LOCAL_FILE" "root@$SERVER:$SERVICE_DIR/app/matching_engine.py"

echo "🔄 Restarting I-MATCH service..."
ssh "root@$SERVER" "systemctl restart fpai-i-match || (cd $SERVICE_DIR && pkill -f 'i-match' || true && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8401 > /var/log/fpai/i-match.log 2>&1 &)"

echo "⏳ Waiting for service to start..."
sleep 3

echo "🧪 Testing service health..."
HEALTH=$(curl -s "http://$SERVER:8401/health" 2>/dev/null)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ I-MATCH service is healthy!"
else
    echo "⚠️ Service may need manual check"
    echo "Response: $HEALTH"
fi

echo ""
echo "🧪 Testing matching endpoint..."
MATCH_TEST=$(curl -s "http://$SERVER:8401/matches/find?customer_id=1" -X POST 2>/dev/null)
if echo "$MATCH_TEST" | grep -q "Internal Server Error"; then
    echo "❌ Matching still broken - check logs"
else
    echo "✅ Matching endpoint responding!"
    echo "Response: $MATCH_TEST"
fi

echo ""
echo "Done! I-MATCH should now use AI Brain for matching."







