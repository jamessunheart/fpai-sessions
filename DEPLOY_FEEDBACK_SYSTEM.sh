#!/bin/bash
#
# 🚀 DEPLOY APPRENTICE FEEDBACK & HARVEST SYSTEM
# Run this on your production server
#

set -e

echo "📦 Deploying Apprentice Feedback System..."
echo "=========================================="

# 1. Update Repository
echo "⬇️  Pulling latest changes..."
git pull origin main

# 2. Set Permissions
echo "🔑 Setting script permissions..."
chmod +x _scripts/harvest-apprentice.py
chmod +x _scripts/apprentice-preflight-check.sh
chmod +x SERVICES/apprentice-feedback/start.sh

# 3. Setup Data Directory
echo "📂 Ensuring data directories exist..."
mkdir -p data/apprentice-feedback
mkdir -p docs/coordination

# 4. Install Dependencies (if needed)
echo "🐍 Installing dependencies..."
if [ -f "SERVICES/apprentice-feedback/requirements.txt" ]; then
    pip3 install -r SERVICES/apprentice-feedback/requirements.txt
else
    pip3 install fastapi uvicorn pydantic
fi

# 5. Restart Service
echo "🔄 Restarting Feedback Service..."
pkill -f "python3 app.py" || true
cd SERVICES/apprentice-feedback
./start.sh

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo "   - Feedback Portal (local): http://localhost:8055"
echo "   - Public URL (after nginx reload): https://fullpotential.ai/harvester"
echo "   - Harvester: _scripts/harvest-apprentice.py"
echo "   - Status: ACTIVE"
echo ""
echo "ℹ️  Reminder: Deploy and reload nginx with the updated nginx.conf to expose /harvester."

