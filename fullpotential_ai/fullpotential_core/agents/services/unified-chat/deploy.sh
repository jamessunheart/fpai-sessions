#!/bin/bash
# Deploy Unified Chat Interface

echo "🚀 Deploying Unified Chat Interface..."

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Start server
echo "🌐 Starting chat server on port 8100..."
python3 main.py &

echo ""
echo "✅ Unified Chat Interface deployed!"
echo ""
echo "📍 Access at: http://localhost:8100"
echo "📍 Sessions connect to: ws://localhost:8100/ws/session/{session-id}"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:8100 in your browser"
echo "2. Connect Claude Code sessions using connect-session.sh"
echo ""
