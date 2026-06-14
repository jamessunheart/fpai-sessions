#!/bin/bash

echo "🌐 Deploying Sovereign AI Dashboard..."
echo "======================================"

# Deploy main.py with dashboard endpoint
echo "📤 Deploying main.py..."
rsync -av /Users/jamessunheart/Development/SERVICES/i-proactive/app/main.py root@198.54.123.234:/opt/fpai/i-proactive/app/

# Deploy dashboard template
echo "📤 Deploying dashboard HTML..."
rsync -av /Users/jamessunheart/Development/SERVICES/i-proactive/app/templates/ root@198.54.123.234:/opt/fpai/i-proactive/app/templates/

echo ""
echo "✅ Files deployed!"
echo ""
echo "🔄 Restarting I PROACTIVE..."

# Restart service
ssh root@198.54.123.234 'bash -s' << 'EOF'
# Kill old process
pkill -f "uvicorn app.main:app.*8400"
sleep 2

# Start new process
cd /opt/fpai/i-proactive
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8400 >/dev/null 2>&1 &
sleep 4

# Test it's running
curl -s http://localhost:8400/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"✅ Service: {data['status']}\")"
EOF

echo ""
echo "======================================"
echo "🎉 Dashboard Deployed!"
echo "======================================"
echo ""
echo "📍 Access the dashboard at:"
echo "   http://198.54.123.234:8400/dashboard"
echo ""
echo "🔍 Or open in browser:"
echo "   open http://198.54.123.234:8400/dashboard"
echo ""
echo "📊 Other endpoints:"
echo "   - System health: http://198.54.123.234:8400/health"
echo "   - Autonomous ops: http://198.54.123.234:8400/autonomous/status"
echo "   - Optimization: http://198.54.123.234:8400/optimization/report"
echo ""
