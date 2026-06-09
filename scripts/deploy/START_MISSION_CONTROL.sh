#!/bin/bash
echo "🚀 Launching Mission Control (The Better Interface)..."

# Check/Install Dependencies
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install fastapi uvicorn jinja2 httpx python-multipart
fi

cd SERVICES/mission-control
echo "🌍 Open your browser to: http://localhost:8000"
python3 app/main.py

