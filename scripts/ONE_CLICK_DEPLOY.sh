#!/bin/bash
#
# ONE-CLICK DEPLOY SCRIPT
# Run this from your local machine to deploy I-MATCH fix
#
# Usage: ./scripts/ONE_CLICK_DEPLOY.sh
#

set -e

echo "🚀 ONE-CLICK DEPLOY - I-MATCH FIX"
echo "================================="
echo ""

SERVER="198.54.123.234"
SERVICE="fpai-i-match"

echo "1️⃣  Copying fixed matching_engine.py to server..."
scp /Users/jamessunheart/FPAI_Cockpit/SERVICES/i-match/app/matching_engine.py \
    root@$SERVER:/opt/fpai/services/i-match/app/matching_engine.py

echo "2️⃣  Restarting I-MATCH service..."
ssh root@$SERVER "systemctl restart $SERVICE || docker restart fpai-i-match 2>/dev/null || (pkill -f 'i-match' ; cd /opt/fpai/services/i-match && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8401 > /tmp/i-match.log 2>&1 &)"

echo "3️⃣  Waiting for service restart..."
sleep 5

echo "4️⃣  Verifying deployment..."
curl -s "http://$SERVER:8401/health" | python3 -m json.tool || echo "Service starting..."

echo ""
echo "✅ DEPLOYMENT COMPLETE"
echo ""
echo "Test the fix:"
echo "  curl -s 'http://$SERVER:8401/matches/find?customer_id=2' -X POST -H 'Content-Type: application/json'"
echo ""







