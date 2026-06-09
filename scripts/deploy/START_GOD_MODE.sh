#!/bin/bash
# Start God Mode (The Council) and Mission Control in the background

# 1. Start Mission Control (Port 8080)
echo "🚀 Starting Mission Control (Port 8080)..."
python3 SERVICES/mission-control/app/main.py > mission_control.log 2>&1 &
MC_PID=$!
echo "   PID: $MC_PID"

# 2. Start God Mode (Port 8085)
echo "🏛️  Starting God Mode (Port 8085)..."
python3 god_mode_server.py > god_mode.log 2>&1 &
GM_PID=$!
echo "   PID: $GM_PID"

echo ""
echo "✅ All systems go!"
echo "👉 God Mode Dashboard: http://localhost:8085"
echo "👉 Mission Control:    http://localhost:8080"
echo ""
echo "Logs:"
echo "  tail -f god_mode.log"
echo "  tail -f mission_control.log"
echo ""
echo "To stop all: kill $MC_PID $GM_PID"
