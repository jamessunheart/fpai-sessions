#!/bin/bash
#
# ARIA DEPLOYMENT SCRIPT
# ======================
#
# Deploys Aria Core, Telegram channel, and Proactive daemon to secondary server.
#
# Usage: ./deploy.sh [SERVER_IP]
#

set -e

SERVER=${1:-162.0.208.88}
DEPLOY_PATH="/opt/fpai/aria"
SERVICE_PORT_CORE=8180
SERVICE_PORT_TELEGRAM=8710

echo "🚀 Deploying Aria to $SERVER..."

# Create directories
ssh root@$SERVER "mkdir -p $DEPLOY_PATH/{core,channels,core/sensors}"

# Copy core files
echo "📦 Copying core files..."
scp -r core/*.py root@$SERVER:$DEPLOY_PATH/core/
scp -r core/sensors/*.py root@$SERVER:$DEPLOY_PATH/core/sensors/
scp -r channels/*.py root@$SERVER:$DEPLOY_PATH/channels/
scp requirements.txt root@$SERVER:$DEPLOY_PATH/
scp run_proactive.py root@$SERVER:$DEPLOY_PATH/

# Copy .env if it exists
if [ -f .env ]; then
    scp .env root@$SERVER:$DEPLOY_PATH/
fi

# Install dependencies
echo "📥 Installing dependencies..."
ssh root@$SERVER "cd $DEPLOY_PATH && pip3 install -r requirements.txt"

# Create systemd service for Aria Core
echo "⚙️ Creating systemd services..."
ssh root@$SERVER "cat > /etc/systemd/system/aria-core.service << 'EOF'
[Unit]
Description=Aria Core API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_PATH
EnvironmentFile=$DEPLOY_PATH/.env
Environment=\"PYTHONPATH=$DEPLOY_PATH\"
ExecStart=/usr/bin/python3 -m uvicorn core.api:app --host 0.0.0.0 --port $SERVICE_PORT_CORE
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Create systemd service for Telegram channel
ssh root@$SERVER "cat > /etc/systemd/system/aria-telegram.service << 'EOF'
[Unit]
Description=Aria Telegram Channel
After=network.target aria-core.service

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_PATH
EnvironmentFile=$DEPLOY_PATH/.env
Environment=\"PYTHONPATH=$DEPLOY_PATH\"
Environment=\"ARIA_CORE_URL=http://localhost:$SERVICE_PORT_CORE\"
ExecStart=/usr/bin/python3 -m uvicorn channels.telegram:app --host 0.0.0.0 --port $SERVICE_PORT_TELEGRAM
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Create systemd service for Proactive daemon
ssh root@$SERVER "cat > /etc/systemd/system/aria-proactive.service << 'EOF'
[Unit]
Description=Aria Proactive Intelligence Daemon
After=network.target aria-core.service

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_PATH
EnvironmentFile=$DEPLOY_PATH/.env
Environment=\"PYTHONPATH=$DEPLOY_PATH\"
ExecStart=/usr/bin/python3 run_proactive.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd and start services
echo "🔄 Starting services..."
ssh root@$SERVER "systemctl daemon-reload"
ssh root@$SERVER "systemctl enable aria-core aria-telegram aria-proactive"
ssh root@$SERVER "systemctl restart aria-core"
sleep 3
ssh root@$SERVER "systemctl restart aria-telegram"
ssh root@$SERVER "systemctl restart aria-proactive"

# Verify
echo "✅ Verifying deployment..."
sleep 2
ssh root@$SERVER "curl -s http://localhost:$SERVICE_PORT_CORE/health | jq ."
ssh root@$SERVER "curl -s http://localhost:$SERVICE_PORT_TELEGRAM/health | jq ."

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Services:"
echo "  aria-core       (port $SERVICE_PORT_CORE) - Main API"
echo "  aria-telegram   (port $SERVICE_PORT_TELEGRAM) - Telegram bot"
echo "  aria-proactive  - Background intelligence daemon"
echo ""
echo "Endpoints:"
echo "  Core API:       http://$SERVER:$SERVICE_PORT_CORE/"
echo "  Telegram:       http://$SERVER:$SERVICE_PORT_TELEGRAM/"
echo "  Proactive:      http://$SERVER:$SERVICE_PORT_CORE/aria/proactive/status"
echo "  Quick Status:   http://$SERVER:$SERVICE_PORT_CORE/aria/quick-status"
echo ""
echo "Logs:"
echo "  journalctl -u aria-core -f"
echo "  journalctl -u aria-telegram -f"
echo "  journalctl -u aria-proactive -f"

