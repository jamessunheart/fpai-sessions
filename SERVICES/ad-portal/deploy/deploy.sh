#!/bin/bash
# Ad Portal Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Ad Portal Deployment"
echo "======================="

# Check environment
if [ "$1" == "production" ]; then
    SERVER="root@198.54.123.234"
    DEPLOY_DIR="/opt/fpai/services/ad-portal"
    echo "Deploying to PRODUCTION ($SERVER)"
else
    echo "Deploying locally (development)"
    cd "$PROJECT_DIR"
    docker-compose up -d --build
    echo "✅ Local deployment complete"
    echo "   API: http://localhost:8800"
    echo "   Frontend: http://localhost:8801"
    exit 0
fi

# Production deployment
echo ""
echo "📦 Syncing files to server..."
rsync -avz --exclude 'venv' --exclude 'node_modules' --exclude '__pycache__' \
    --exclude '.git' --exclude 'dist' --exclude '.env' \
    "$PROJECT_DIR/" "$SERVER:$DEPLOY_DIR/"

echo ""
echo "🔧 Setting up on server..."
ssh "$SERVER" << 'ENDSSH'
cd /opt/fpai/services/ad-portal

# Install Python dependencies
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi
pip install -r requirements.txt

# Build frontend
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

# Create systemd service if not exists
if [ ! -f "/etc/systemd/system/ad-portal.service" ]; then
    cat > /etc/systemd/system/ad-portal.service << EOF
[Unit]
Description=Ad Portal API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/services/ad-portal
ExecStart=/opt/fpai/services/ad-portal/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8800
Restart=always
RestartSec=10
Environment=PATH=/opt/fpai/services/ad-portal/venv/bin:/usr/local/bin:/usr/bin

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable ad-portal
fi

# Restart service
systemctl restart ad-portal

echo "Waiting for service to start..."
sleep 5

# Health check
if curl -sf http://localhost:8800/health > /dev/null; then
    echo "✅ Ad Portal API is healthy"
else
    echo "❌ Health check failed"
    systemctl status ad-portal
    exit 1
fi

ENDSSH

echo ""
echo "✅ Production deployment complete!"
echo "   API: http://198.54.123.234:8800"
echo "   Docs: http://198.54.123.234:8800/docs"


