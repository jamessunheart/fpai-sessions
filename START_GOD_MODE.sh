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

# FIX: NPM Permission Hell
# If global cache is broken, we use a local project-level cache to bypass it.
export npm_config_cache=$(pwd)/.npm-local-cache

if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/vite" ]; then
    echo "   Installing npm packages (using local cache)..."
    
    # Clean start
    rm -rf node_modules package-lock.json
    
    # Install with local cache to avoid EACCES errors
    npm install --cache .npm-local-cache --prefer-offline --no-audit
    
    if [ $? -ne 0 ]; then
        echo "⚠️  Install failed. Trying fallback network install..."
        npm install --cache .npm-local-cache --force
    fi
fi

# 3. Launch
echo "🚀 Ignition..."

# Run Backend
cd ../backend
export PYTHONUNBUFFERED=1
python3 main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Run Frontend
cd ../frontend
echo "🌍 UI Starting..."
echo "👉 Try: http://localhost:5173"
echo "👉 Try: http://127.0.0.1:5173"
echo "---------------------------------------------------"

if [ -f "./node_modules/.bin/vite" ]; then
    ./node_modules/.bin/vite --host
else
    echo "❌ CRITICAL ERROR: npm install failed even with local cache."
    echo "   Please run this command to fix your system permissions:"
    echo "   sudo chown -R \$(whoami) ~/.npm"
    kill $BACKEND_PID
    exit 1
fi

kill $BACKEND_PID
