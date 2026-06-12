#!/bin/bash
# Proactive Monitor Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Proactive Monitor Deployment"
echo "==============================="

# Check environment
if [ "$1" == "production" ]; then
    SERVER="root@198.54.123.234"
    DEPLOY_DIR="/opt/fpai/services/proactive-monitor"
    echo "Deploying to PRODUCTION ($SERVER)"
else
    echo "Usage: ./deploy.sh production"
    exit 1
fi

# Production deployment
echo ""
echo "📦 Syncing files to server..."
rsync -avz --exclude 'venv' --exclude '__pycache__' \
    --exclude '.git' --exclude '.env' \
    "$PROJECT_DIR/" "$SERVER:$DEPLOY_DIR/"

echo ""
echo "🔧 Setting up on server..."
ssh "$SERVER" << 'ENDSSH'
cd /opt/fpai/services/proactive-monitor

# Create .env if not exists (already has good defaults)
if [ ! -f ".env" ]; then
    echo "Using default .env from source"
fi

# Install Python dependencies
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi
pip install -r requirements.txt

# Create systemd service if not exists
if [ ! -f "/etc/systemd/system/fpai-proactive-monitor.service" ]; then
    cat > /etc/systemd/system/fpai-proactive-monitor.service << EOF
[Unit]
Description=FPAI Proactive Monitor Service
After=network.target fpai-chief-of-staff.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/services/proactive-monitor
ExecStart=/opt/fpai/services/proactive-monitor/venv/bin/python -m app.main
Restart=always
RestartSec=10
Environment=PATH=/opt/fpai/services/proactive-monitor/venv/bin:/usr/local/bin:/usr/bin

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable fpai-proactive-monitor
fi

# Restart service
systemctl restart fpai-proactive-monitor

echo "Waiting for service to start..."
sleep 5

# Health check
if curl -sf http://localhost:8108/health > /dev/null; then
    echo "✅ Proactive Monitor Service is healthy"
else
    echo "❌ Health check failed"
    systemctl status fpai-proactive-monitor
    journalctl -u fpai-proactive-monitor -n 50
    exit 1
fi

ENDSSH

echo ""
echo "✅ Production deployment complete!"
echo "   Health: http://198.54.123.234:8108/health"
echo "   Status: http://198.54.123.234:8108/status"
echo "   Docs: http://198.54.123.234:8108/docs"
echo ""
echo "🔄 The monitor will start checking services every 5 minutes automatically"
echo "   Signals will be sent to Chief of Staff → filtered → alerted via Telegram"
