#!/bin/bash

# Start I PROACTIVE service

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 STARTING I PROACTIVE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "📝 REQUIRED: Edit .env and add your API keys:"
    echo "   - ANTHROPIC_API_KEY (for Claude)"
    echo "   - OPENAI_API_KEY (for GPT-4)"
    echo "   - GOOGLE_API_KEY (for Gemini)"
    echo ""
    echo "Get API keys from:"
    echo "   - Anthropic: https://console.anthropic.com/settings/keys"
    echo "   - OpenAI: https://platform.openai.com/api-keys"
    echo "   - Google: https://makersuite.google.com/app/apikey"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check for at least one API key
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null && \
   ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null && \
   ! grep -q "GOOGLE_API_KEY=AI" .env 2>/dev/null; then
    echo "⚠️  No AI model API keys configured in .env"
    echo ""
    echo "Edit .env and add at least one of:"
    echo "   - ANTHROPIC_API_KEY=sk-ant-xxxxx"
    echo "   - OPENAI_API_KEY=sk-xxxxx"
    echo "   - GOOGLE_API_KEY=AIxxxxx"
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
echo "🌐 I PROACTIVE STARTING..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Service will run at: http://localhost:8400"
echo "API Documentation: http://localhost:8400/docs"
echo ""
echo "UBIC Endpoints:"
echo "  • /health        - Service health status"
echo "  • /capabilities  - What this service can do"
echo "  • /state         - Current operational state"
echo "  • /dependencies  - Required services"
echo "  • /message       - Inter-service communication"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the service
uvicorn app.main:app --reload --port 8400
