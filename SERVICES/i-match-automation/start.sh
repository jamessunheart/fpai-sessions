#!/bin/bash
# I MATCH Automation Suite - Start Script

echo "🤖 Starting I MATCH Automation Suite..."
echo ""

cd "$(dirname "$0")"

# Check for .env
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Copy .env.example to .env and add your ANTHROPIC_API_KEY"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Start service
echo "🚀 Launching service on port 8510..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8510 &
PID=$!

# Wait and check
sleep 3

if curl -s http://localhost:8510/health > /dev/null 2>&1; then
    echo ""
    echo "✅ I MATCH Automation Suite RUNNING"
    echo ""
    echo "📊 Dashboard: http://localhost:8510"
    echo "📚 API Docs:  http://localhost:8510/docs"
    echo "🔍 Health:    http://localhost:8510/health"
    echo ""
    echo "Process ID: $PID"
    echo "Logs: /tmp/i-match-automation.log"
    echo ""
    echo "To stop: kill $PID"
else
    echo ""
    echo "❌ Failed to start. Check /tmp/i-match-automation.log"
    exit 1
fi
