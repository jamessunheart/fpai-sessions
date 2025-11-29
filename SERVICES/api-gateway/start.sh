#!/bin/bash
# Start API Gateway

cd "$(dirname "$0")"

# Kill existing process
pkill -f "python3.*8400" 2>/dev/null || true

# Start service
nohup python3 app.py > api-gateway.log 2>&1 &

echo "✅ API Gateway started on port 8400"
echo "   Dashboard: http://localhost:8400"
echo "   Logs: tail -f api-gateway.log"

