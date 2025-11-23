#!/bin/bash

# Cleanup
pkill -f "uvicorn" || true
pkill -f "vite" || true

echo "🏛️  Initializing GOD MODE GUI..."

# 1. Check Backend Deps
echo "📦 Checking Backend..."
if ! python3 -c "import fastapi; import uvicorn; import websockets" &> /dev/null; then
    pip3 install fastapi uvicorn websockets
fi

# 2. Check Frontend Deps
echo "📦 Checking Frontend..."
cd SERVICES/god-mode/frontend
if [ ! -d "node_modules" ]; then
    echo "   Installing npm packages (this may take a moment)..."
    npm install
fi

# 3. Launch
echo "🚀 Ignition..."

# Run Backend in background (Port 3000)
cd ../backend
# Force unbuffered output to see errors
export PYTHONUNBUFFERED=1
python3 main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Run Frontend (Vite) (Port 5173)
cd ../frontend
echo "🌍 UI Starting..."
echo "👉 Try: http://localhost:5173"
echo "👉 Try: http://127.0.0.1:5173"
echo "---------------------------------------------------"

# Run Vite with host binding
npm run dev

# Cleanup on exit
kill $BACKEND_PID
