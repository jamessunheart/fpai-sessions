#!/bin/bash

# Start both Alerts and Chief of Staff services
# Run in separate terminal windows

echo "🚀 Starting FPAI Intelligence Services"
echo "======================================"
echo ""

# Check if already running
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Alerts service already running on port 8765"
else
    echo "Starting Alerts service on port 8765..."
    cd ../alerts
    python3 -m app.main > alerts.log 2>&1 &
    ALERTS_PID=$!
    echo "  ✓ Alerts service started (PID: $ALERTS_PID)"
    cd - > /dev/null
fi

sleep 2

if lsof -Pi :8107 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Chief of Staff already running on port 8107"
else
    echo "Starting Chief of Staff on port 8107..."
    python3 -m app.main > chief.log 2>&1 &
    CHIEF_PID=$!
    echo "  ✓ Chief of Staff started (PID: $CHIEF_PID)"
fi

sleep 3

echo ""
echo "Checking health..."

if curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo "  ✓ Alerts service: healthy"
else
    echo "  ✗ Alerts service: not responding"
fi

if curl -s http://localhost:8107/health > /dev/null 2>&1; then
    echo "  ✓ Chief of Staff: healthy"
else
    echo "  ✗ Chief of Staff: not responding"
fi

echo ""
echo "======================================"
echo ""
echo "Services running!"
echo ""
echo "  Alerts:        http://localhost:8765"
echo "  Chief of Staff: http://localhost:8107"
echo "  Dashboard:     http://localhost:8107/dashboard"
echo ""
echo "Logs:"
echo "  Alerts:        tail -f ../alerts/alerts.log"
echo "  Chief of Staff: tail -f chief.log"
echo ""
echo "To test: ./test_chief_of_staff.sh"
echo ""
