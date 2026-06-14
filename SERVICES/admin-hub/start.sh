#!/bin/bash
# Start Admin Hub

cd "$(dirname "$0")"

# Kill existing process
pkill -f "python3.*8888" 2>/dev/null || true
sleep 1

# Start service
nohup python3 app.py > admin-hub.log 2>&1 &

echo "✅ Admin Hub started on port 8888"
echo "   URL: https://fullpotential.ai/admin"
echo "   Logs: tail -f admin-hub.log"

