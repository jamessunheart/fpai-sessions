#!/bin/bash

# Start Web Dashboard for Multi-Session Coordination

cd "$(dirname "$0")"

echo "🚀 Starting Claude Code Coordination Web Dashboard..."
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo ""
echo "✅ Starting server on http://localhost:8030"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║  🌐 Claude Code Coordination Dashboard                       ║"
echo "║                                                              ║"
echo "║  📊 Open in your browser:                                    ║"
echo "║     http://localhost:8030                                    ║"
echo "║                                                              ║"
echo "║  Features:                                                   ║"
echo "║  ✓ Real-time monitoring of all 13 sessions                  ║"
echo "║  ✓ Auto-refresh every 5 seconds                             ║"
echo "║  ✓ Chat interface to send broadcasts                        ║"
echo "║  ✓ Server health monitoring                                 ║"
echo "║  ✓ Session coordination status                              ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py
