#!/bin/bash
# Deploy Mission Control v2.0 System
# Run this on the server after git pull

set -e

echo "🚀 Deploying Mission Control v2.0..."
echo "======================================="

# Navigate to workspace
cd /root/FPAI_Cockpit

# 1. Install Mission Control Dependencies
echo ""
echo "📦 Installing Mission Control dependencies..."
cd SERVICES/mission-control
pip3 install -r requirements.txt

# 2. Create data directories
echo ""
echo "📁 Creating data directories..."
mkdir -p data/claims
mkdir -p data/status
mkdir -p static
mkdir -p templates

# 3. Stop old services
echo ""
echo "⏸️  Stopping old services..."
pkill -f "mission-control/app.py" || true
fuser -k 8700/tcp 2>/dev/null || true

pkill -f "SERVICES/harvester/app.py" || true
fuser -k 8055/tcp 2>/dev/null || true

# 4. Update Harvester dependencies
echo ""
echo "📦 Updating Harvester dependencies..."
cd /root/FPAI_Cockpit/SERVICES/harvester
pip3 install -r requirements.txt

# 5. Start Mission Control
echo ""
echo "🎯 Starting Mission Control (Port 8700)..."
cd /root/FPAI_Cockpit/SERVICES/mission-control
nohup python3 app.py > mission-control.log 2>&1 &
sleep 2

# Verify
if curl -s http://127.0.0.1:8700/health > /dev/null; then
    echo "   ✅ Mission Control healthy"
else
    echo "   ❌ Mission Control failed to start"
    echo "   Check logs: tail -f mission-control.log"
    exit 1
fi

# 6. Start Harvester
echo ""
echo "🚜 Starting Harvester (Port 8055)..."
cd /root/FPAI_Cockpit/SERVICES/harvester
nohup python3 app.py > feedback.log 2>&1 &
sleep 2

# Verify
if curl -s http://127.0.0.1:8055/health > /dev/null; then
    echo "   ✅ Harvester healthy"
else
    echo "   ❌ Harvester failed to start"
    echo "   Check logs: tail -f feedback.log"
    exit 1
fi

# 7. Update Nginx
echo ""
echo "🌐 Updating Nginx configuration..."
cd /root/FPAI_Cockpit
cp nginx.conf /etc/nginx/sites-available/fullpotential.ai
sudo nginx -t && sudo systemctl reload nginx
echo "   ✅ Nginx reloaded"

# 8. Summary
echo ""
echo "======================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "Services Running:"
echo "  - Mission Control: http://fullpotential.ai/missions (Port 8700)"
echo "  - Harvester: http://fullpotential.ai/services/harvester (Port 8055)"
echo ""
echo "Test URLs:"
echo "  curl https://fullpotential.ai/missions"
echo "  curl http://127.0.0.1:8700/api/missions"
echo ""
echo "Logs:"
echo "  tail -f /root/FPAI_Cockpit/SERVICES/mission-control/mission-control.log"
echo "  tail -f /root/FPAI_Cockpit/SERVICES/harvester/feedback.log"
echo ""

