#!/bin/bash
# Start Mission Hub Service
# Port: 8700

cd "$(dirname "$0")"

# Kill any existing process on our port
pkill -f "mission-hub/app.py" 2>/dev/null
fuser -k 8700/tcp 2>/dev/null
sleep 1

# Start service
nohup python3 app.py > mission-hub.log 2>&1 &

echo "✅ Mission Hub started on port 8700"
echo "   View: http://localhost:8700"
echo "   Logs: tail -f mission-hub.log"

