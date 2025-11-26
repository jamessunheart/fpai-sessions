#!/bin/bash
# ============================================================================
# MISSION HUB DEPLOYMENT SCRIPT
# ============================================================================
# Deploys the Mission Hub service (replaces old mission-control)
#
# Usage: ./DEPLOY_MISSION_HUB.sh
# ============================================================================

set -e

echo "🚀 Deploying Mission Hub..."
echo "=============================================="

# Navigate to project root
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

# 1. Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r SERVICES/mission-hub/requirements.txt --quiet

# 2. Stop old mission-control if running
echo ""
echo "🛑 Stopping old services..."
pkill -f "mission-control/app.py" 2>/dev/null || true
pkill -f "mission-hub/app.py" 2>/dev/null || true
fuser -k 8700/tcp 2>/dev/null || true
sleep 1

# 3. Start Mission Hub
echo ""
echo "⚡ Starting Mission Hub..."
cd SERVICES/mission-hub
chmod +x start.sh
./start.sh
cd "$PROJECT_ROOT"

# 4. Wait and verify
echo ""
echo "🔍 Verifying..."
sleep 2

if curl -s http://127.0.0.1:8700/health | grep -q "healthy"; then
    echo "✅ Mission Hub is healthy!"
else
    echo "⚠️  Health check failed. Check logs:"
    echo "   tail -f SERVICES/mission-hub/mission-hub.log"
    exit 1
fi

# 5. Summary
echo ""
echo "=============================================="
echo "✅ MISSION HUB DEPLOYED SUCCESSFULLY"
echo "=============================================="
echo ""
echo "📍 Endpoints:"
echo "   • Mission Board:  http://localhost:8700/"
echo "   • API:            http://localhost:8700/api/missions"
echo "   • Health:         http://localhost:8700/health"
echo ""
echo "📝 Logs:"
echo "   tail -f SERVICES/mission-hub/mission-hub.log"
echo ""
echo "🔗 Nginx Routes (configure if needed):"
echo "   /missions → http://127.0.0.1:8700"
echo ""

