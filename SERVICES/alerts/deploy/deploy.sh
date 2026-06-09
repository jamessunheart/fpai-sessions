#!/bin/bash
# Alerts Service Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Alerts Service Deployment"
echo "============================"

# Check environment
if [ "$1" == "production" ]; then
    SERVER="root@198.54.123.234"
    DEPLOY_DIR="/opt/fpai/services/alerts"
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
cd /opt/fpai/services/alerts

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env file - YOU MUST UPDATE CREDENTIALS!"
    cat > .env << EOF
# Alerts Service Configuration
SERVICE_NAME=alerts
DROPLET_ID=106
APP_VERSION=1.0.0
PORT=8766
DEBUG=false

# Telegram Configuration
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_STEWARD_CHAT_ID=YOUR_CHAT_ID_HERE

# Twilio Configuration (SMS)
TWILIO_ACCOUNT_SID=YOUR_TWILIO_SID_HERE
TWILIO_AUTH_TOKEN=YOUR_TWILIO_TOKEN_HERE
TWILIO_PHONE_NUMBER=+1234567890

# Queue Configuration
MAX_QUEUE_SIZE=1000
RATE_LIMIT_WINDOW_SECONDS=60

# Channel Rate Limits
TELEGRAM_RATE_LIMIT=30
SMS_RATE_LIMIT=5

# Retry Configuration
TELEGRAM_RETRY_COUNT=3
TELEGRAM_RETRY_DELAY=5
SMS_RETRY_COUNT=2
SMS_RETRY_DELAY=10
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
if [ ! -f "/etc/systemd/system/fpai-alerts.service" ]; then
    cat > /etc/systemd/system/fpai-alerts.service << EOF
[Unit]
Description=FPAI Alerts Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/services/alerts
ExecStart=/opt/fpai/services/alerts/venv/bin/python -m app.main
Restart=always
RestartSec=10
Environment=PATH=/opt/fpai/services/alerts/venv/bin:/usr/local/bin:/usr/bin

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable fpai-alerts
fi

# Restart service
systemctl restart fpai-alerts

echo "Waiting for service to start..."
sleep 5

# Health check
if curl -sf http://localhost:8766/health > /dev/null; then
    echo "✅ Alerts Service is healthy"
else
    echo "❌ Health check failed"
    systemctl status fpai-alerts
    journalctl -u fpai-alerts -n 50
    exit 1
fi

ENDSSH

echo ""
echo "✅ Production deployment complete!"
echo "   Health: http://198.54.123.234:8766/health"
echo "   Docs: http://198.54.123.234:8766/docs"
echo ""
echo "⚠️  IMPORTANT: Update /opt/fpai/services/alerts/.env on server with real credentials!"
