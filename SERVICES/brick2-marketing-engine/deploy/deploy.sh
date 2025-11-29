#!/bin/bash
# BRICK 2 Marketing Engine - Deployment Script
# Deploys to fullpotential.ai/services/marketing

set -e

echo "🚀 BRICK 2 Marketing Engine Deployment"
echo "======================================="

# Configuration
SERVER="198.54.123.234"
DEPLOY_PATH="/root/FPAI_Cockpit/SERVICES/brick2-marketing-engine"
LOCAL_PATH="$(dirname "$0")/.."

# Step 1: Sync files to server
echo ""
echo "📦 Syncing files to server..."
rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
    "$LOCAL_PATH/" "root@$SERVER:$DEPLOY_PATH/"

# Step 2: Install dependencies
echo ""
echo "📥 Installing dependencies..."
ssh root@$SERVER "cd $DEPLOY_PATH && pip3 install -r requirements.txt"

# Step 3: Restart BRICK 2 API
echo ""
echo "🔄 Restarting BRICK 2 API..."
ssh root@$SERVER "pkill -f 'uvicorn app.main:app.*8700' || true; sleep 2"
ssh root@$SERVER "cd $DEPLOY_PATH && PYTHONPATH=/root/FPAI_Cockpit nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8700 > /var/log/brick2-api.log 2>&1 &"

# Step 4: Setup autopilot daemon (optional)
echo ""
echo "🤖 Setting up autopilot daemon..."
ssh root@$SERVER "cp $DEPLOY_PATH/deploy/autopilot.service /etc/systemd/system/ || true"
ssh root@$SERVER "systemctl daemon-reload || true"
ssh root@$SERVER "systemctl enable brick2-autopilot || true"
# Note: Don't start automatically - run manually first to test
# ssh root@$SERVER "systemctl start brick2-autopilot"

# Step 5: Update nginx for /services/marketing route
echo ""
echo "🌐 Updating nginx configuration..."
ssh root@$SERVER "cat >> /etc/nginx/sites-available/fullpotential.ai << 'NGINX_CONF' || true

    # BRICK 2 Marketing API
    location /api/brick2/ {
        proxy_pass http://localhost:8700/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
NGINX_CONF"

# Step 6: Reload nginx
echo ""
echo "🔄 Reloading nginx..."
ssh root@$SERVER "nginx -t && systemctl reload nginx || true"

# Step 7: Verify deployment
echo ""
echo "✅ Verifying deployment..."
sleep 3
curl -s "http://$SERVER:8700/health" | python3 -m json.tool

echo ""
echo "======================================="
echo "✅ BRICK 2 deployed successfully!"
echo ""
echo "Endpoints:"
echo "  - API: http://$SERVER:8700/"
echo "  - Health: http://$SERVER:8700/health"
echo "  - Marketing Page: https://fullpotential.ai/services/marketing"
echo ""
echo "To start autopilot daemon:"
echo "  ssh root@$SERVER 'systemctl start brick2-autopilot'"
echo ""

