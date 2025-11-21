#!/bin/bash

# Start I MATCH service

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 STARTING I MATCH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "📝 REQUIRED: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   Get key: https://console.anthropic.com/settings/keys"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check for API key
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
    echo "⚠️  ANTHROPIC_API_KEY not configured in .env"
    echo ""
    echo "Edit .env and add: ANTHROPIC_API_KEY=sk-ant-xxxxx"
    exit 1
fi

echo "✅ Environment configured"
echo ""

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💰 I MATCH STARTING..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Service: http://localhost:8401"
echo "API Docs: http://localhost:8401/docs"
echo ""
echo "Revenue Model: 20% Commission"
echo "Target Month 1: $40-150K"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the service
uvicorn app.main:app --reload --port 8401
