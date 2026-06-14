#!/bin/bash

echo "💪 Launching Muscle (Autonomous Executor)..."

# Check dependencies
if ! python3 -c "import fastapi; import uvicorn; import anthropic" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install fastapi uvicorn anthropic pydantic-settings
fi

cd SERVICES/autonomous-executor

# Ensure .env exists to avoid crashes
if [ ! -f .env ]; then
    echo "ANTHROPIC_API_KEY=mock-key-for-visualization" > .env
fi

# Run
export PYTHONUNBUFFERED=1
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8400 --reload

