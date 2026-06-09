#!/bin/bash
# =============================================================================
# DEPLOY CORACLE PREDICTION ENGINE TO PRODUCTION
# =============================================================================
# Deploys the Coracle engine to primary server (198.54.123.234)
#
# Usage: ./deploy-coracle-engine.sh
# Requires: SSH access to 198.54.123.234

set -e

SERVER="198.54.123.234"
SERVICE_NAME="fpai-coracle-engine"
SERVICE_PORT="8650"
DEPLOY_PATH="/opt/fpai/services/coracle-engine"
LOCAL_PATH="/Users/jamessunheart/FPAI_Cockpit/SERVICES/coracle-engine"

echo "🔮 Deploying Coracle Prediction Engine..."
echo ""
echo "Server: $SERVER"
echo "Port: $SERVICE_PORT"
echo "Path: $DEPLOY_PATH"
echo ""

# Check if local directory exists
if [ ! -d "$LOCAL_PATH" ]; then
    echo "❌ Error: Local path not found: $LOCAL_PATH"
    exit 1
fi

# Create remote directory
echo "📁 Creating deployment directory..."
ssh "root@$SERVER" "mkdir -p $DEPLOY_PATH"

# Sync files
echo "📤 Syncing files to server..."
rsync -avz --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '.env' \
    "$LOCAL_PATH/" "root@$SERVER:$DEPLOY_PATH/"

# Create systemd service file
echo "⚙️ Creating systemd service..."
ssh "root@$SERVER" "cat > /etc/systemd/system/$SERVICE_NAME.service << 'EOF'
[Unit]
Description=Coracle Prediction Engine
After=network.target
Wants=fpai-whaletrack-magnet.service

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_PATH
Environment=\"PYTHONPATH=$DEPLOY_PATH\"
Environment=\"CORACLE_PORT=$SERVICE_PORT\"
Environment=\"WHALETRACK_URL=http://localhost:8600\"
Environment=\"DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/coracle\"
Environment=\"REDIS_URL=redis://localhost:6379\"
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port $SERVICE_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Install dependencies
echo "📦 Installing dependencies..."
ssh "root@$SERVER" "cd $DEPLOY_PATH && pip3 install -r requirements.txt --quiet"

# Create database if needed
echo "🗄️ Setting up database..."
ssh "root@$SERVER" "sudo -u postgres psql -c 'CREATE DATABASE coracle;' 2>/dev/null || true"

# Reload and start service
echo "🚀 Starting service..."
ssh "root@$SERVER" "systemctl daemon-reload && systemctl enable $SERVICE_NAME && systemctl restart $SERVICE_NAME"

# Wait for startup
echo "⏳ Waiting for service to start..."
sleep 5

# Health check
echo "🧪 Running health check..."
HEALTH=$(ssh "root@$SERVER" "curl -s http://localhost:$SERVICE_PORT/health" 2>/dev/null)

if echo "$HEALTH" | grep -q "healthy"; then
    echo "✅ Coracle Engine is healthy!"
    echo ""
    echo "Health response:"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo "⚠️ Health check returned unexpected response"
    echo "Response: $HEALTH"
    echo ""
    echo "Checking logs..."
    ssh "root@$SERVER" "journalctl -u $SERVICE_NAME -n 30 --no-pager"
fi

echo ""
echo "📊 Service status:"
ssh "root@$SERVER" "systemctl status $SERVICE_NAME --no-pager | head -15"

echo ""
echo "🔗 Endpoints:"
echo "   Health: http://$SERVER:$SERVICE_PORT/health"
echo "   Analyze: POST http://$SERVER:$SERVICE_PORT/api/analyze"
echo "   Signals: GET http://$SERVER:$SERVICE_PORT/api/signals/{symbol}"
echo "   Contracts: GET http://$SERVER:$SERVICE_PORT/api/contracts"
echo "   WebSocket: ws://$SERVER:$SERVICE_PORT/ws/stream"
echo ""
echo "Done! 🎉"


