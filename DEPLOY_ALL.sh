#!/bin/bash
#
# 🚀 DEPLOY FULL POTENTIAL SYSTEM
# Updates Dashboard, Feedback Service, and Nginx Config
#

set -e

echo "📦 Deploying Full Potential System..."
echo "===================================="

# 1. Update Repo
git pull origin main

# 2. Deploy Master Dashboard
echo "🎨 Deploying Master Dashboard..."
cd DASHBOARDS/master
pip3 install -r requirements.txt
pkill -f "DASHBOARDS/master/app.py" || true
nohup python3 app.py > dashboard.log 2>&1 &
cd ../..

# 3. Deploy Harvester Service
echo "🚜 Deploying Harvester..."
cd SERVICES/harvester
pip3 install -r requirements.txt
pkill -f "SERVICES/harvester/app.py" || true
# Ensure it listens on 0.0.0.0
sed -i 's/host="127.0.0.1"/host="0.0.0.0"/' app.py
nohup python3 app.py > feedback.log 2>&1 &
cd ../..

echo ""
echo "✅ Services Deployed!"
echo "   - Master Dashboard: http://localhost:3000"
echo "   - Harvester Service: http://localhost:8055"
echo ""
echo "⚠️  Reminder: Update Nginx config manually if changed:"
echo "   cp nginx.conf /etc/nginx/sites-available/fullpotential.ai"
echo "   nginx -t && systemctl reload nginx"
