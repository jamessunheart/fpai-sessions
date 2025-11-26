#!/bin/bash
# Start Mission Control Service

cd "$(dirname "$0")"

# Kill any existing process
pkill -f "mission-control/app.py"
fuser -k 8700/tcp 2>/dev/null

# Start service
nohup python3 app.py > mission-control.log 2>&1 &

echo "✅ Mission Control started on port 8700"
echo "   Logs: tail -f mission-control.log"
