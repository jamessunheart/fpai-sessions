#!/bin/bash
# Chief of Staff Service Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Chief of Staff Service Deployment"
echo "====================================="

# Check environment
if [ "$1" == "production" ]; then
    SERVER="root@198.54.123.234"
    DEPLOY_DIR="/opt/fpai/services/chief-of-staff"
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
cd /opt/fpai/services/chief-of-staff

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Chief of Staff Service Configuration
SERVICE_NAME=chief-of-staff
DROPLET_ID=107
APP_VERSION=1.0.0
PORT=8107
DEBUG=false

# Alerts Integration
ALERTS_SERVICE_URL=http://localhost:8766

# Decision Filter (30-day goal relevance)
DECISION_WINDOW_DAYS=30
DECISION_FILTER_KEYWORDS=revenue,booking,conversion,user,payment,zen village,retreat,proof,clarity,error,critical,down

# Urgency Thresholds
URGENT_THRESHOLD_REVENUE_DROP=0.20
URGENT_THRESHOLD_ERROR_RATE=0.05
URGENT_THRESHOLD_UPTIME=95.0

# Notification Schedule
DIGEST_TIME=09:00
SUMMARY_DAY=monday
SUMMARY_TIME=09:00

# Learning
TRACK_USER_ACTIONS=true
AUTO_SUGGEST_THRESHOLD=3

# Signal Storage
MAX_SIGNALS_HISTORY=10000
SIGNAL_RETENTION_DAYS=90
EOF
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
if [ ! -f "/etc/systemd/system/fpai-chief-of-staff.service" ]; then
    cat > /etc/systemd/system/fpai-chief-of-staff.service << EOF
[Unit]
Description=FPAI Chief of Staff Service
After=network.target fpai-alerts.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/services/chief-of-staff
ExecStart=/opt/fpai/services/chief-of-staff/venv/bin/python -m app.main
Restart=always
RestartSec=10
Environment=PATH=/opt/fpai/services/chief-of-staff/venv/bin:/usr/local/bin:/usr/bin

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable fpai-chief-of-staff
fi

# Restart service
systemctl restart fpai-chief-of-staff

echo "Waiting for service to start..."
sleep 5

# Health check
if curl -sf http://localhost:8107/health > /dev/null; then
    echo "✅ Chief of Staff Service is healthy"
else
    echo "❌ Health check failed"
    systemctl status fpai-chief-of-staff
    journalctl -u fpai-chief-of-staff -n 50
    exit 1
fi

ENDSSH

echo ""
echo "✅ Production deployment complete!"
echo "   Health: http://198.54.123.234:8107/health"
echo "   Dashboard: http://198.54.123.234:8107/dashboard"
echo "   Docs: http://198.54.123.234:8107/docs"
