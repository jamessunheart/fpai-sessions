#!/bin/bash

# 🚀 START THE FLYWHEEL - Launch Script
# This starts the autonomous building + revenue generation loop

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 STARTING THE FLYWHEEL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check environment
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "📝 REQUIRED: Edit .env and add your ANTHROPIC_API_KEY"
    echo ""
    echo "Get your key: https://console.anthropic.com/settings/keys"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check for API key
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
    echo "⚠️  ANTHROPIC_API_KEY not configured in .env"
    echo ""
    echo "Edit .env and add:"
    echo "ANTHROPIC_API_KEY=sk-ant-xxxxx"
    echo ""
    echo "Get your key: https://console.anthropic.com/settings/keys"
    exit 1
fi

echo "✅ Environment configured"
echo ""

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 AUTONOMOUS EXECUTOR STARTING..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Service will run at: http://localhost:8400"
echo ""
echo "To build I PROACTIVE autonomously, open a new terminal and run:"
echo ""
echo "curl -X POST http://localhost:8400/executor/build-droplet \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"architect_intent\": \"Build I PROACTIVE orchestration brick with CrewAI for agent coordination, Mem0.ai for persistent memory, multi-model routing, and strategic decision engine\","
echo "    \"droplet_id\": 20,"
echo "    \"droplet_name\": \"i-proactive\","
echo "    \"approval_mode\": \"checkpoints\""
echo "  }'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the service
uvicorn app.main:app --reload --port 8400
