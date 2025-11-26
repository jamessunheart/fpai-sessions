#!/bin/bash
# Deploy WhaleTrack + Magnet Trading Engine to Server (Port 8600)

set -e

SERVER="root@198.54.123.234"
SERVICE_NAME="whaletrack-magnet"
PORT=8600
DEPLOY_DIR="/opt/fpai/services/whaletrack-magnet"

echo "🐋 Deploying WhaleTrack + Magnet Engine to Server"
echo "=================================================="

# 1. Create deployment directory on server
echo "📁 Creating deployment directory..."
ssh $SERVER "mkdir -p $DEPLOY_DIR"

# 2. Copy backend code
echo "📦 Copying backend code..."
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
  backend/ $SERVER:$DEPLOY_DIR/

# 3. Copy deployment files
echo "📋 Copying deployment files..."
scp deployment/Dockerfile $SERVER:$DEPLOY_DIR/
scp backend/requirements.txt $SERVER:$DEPLOY_DIR/

# 4. Create systemd service
echo "⚙️  Creating systemd service..."
ssh $SERVER "cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=WhaleTrack + Magnet Trading Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

# 5. Install dependencies
echo "📚 Installing Python dependencies..."
ssh $SERVER "cd $DEPLOY_DIR && pip3 install -r requirements.txt"

# 6. Stop old service if running
echo "🛑 Stopping old service (if running)..."
ssh $SERVER "systemctl stop ${SERVICE_NAME} || true"

# 7. Reload systemd and start service
echo "🚀 Starting service..."
ssh $SERVER "systemctl daemon-reload"
ssh $SERVER "systemctl enable ${SERVICE_NAME}"
ssh $SERVER "systemctl start ${SERVICE_NAME}"

# 8. Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 5

# 9. Check status
echo "🔍 Checking service status..."
ssh $SERVER "systemctl status ${SERVICE_NAME} --no-pager || true"

# 10. Verify health endpoint
echo "🏥 Verifying health endpoint..."
sleep 2
ssh $SERVER "curl -f http://localhost:${PORT}/health || echo 'Health check failed'"

echo ""
echo "✅ Deployment complete!"
echo "📡 Service running on: http://198.54.123.234:${PORT}"
echo "🔍 Check status: ssh $SERVER 'systemctl status ${SERVICE_NAME}'"
echo "📋 View logs: ssh $SERVER 'journalctl -u ${SERVICE_NAME} -f'"
echo ""
echo "🐋 WhaleTrack + Magnet Engine is LIVE!"

