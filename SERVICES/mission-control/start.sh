#!/bin/bash
# START MISSION CONTROL (Port 8080)
set -e

cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "🚀 Launching Mission Control on Port 8080..."
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

