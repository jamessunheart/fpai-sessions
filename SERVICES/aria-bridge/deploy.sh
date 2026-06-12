#!/bin/bash
# Aria Bridge Deployment Script
# Deploys to Secondary Server (162.0.208.88)

set -e

echo "════════════════════════════════════════════"
echo "   ARIA BRIDGE - Deployment"
echo "   Bridge Across Dimensions"
echo "════════════════════════════════════════════"

DEPLOY_SERVER="162.0.208.88"
DEPLOY_PATH="/opt/fpai/aria-bridge"
SERVICE_NAME="aria-bridge"

# Check if we can connect
echo "📡 Checking connection to $DEPLOY_SERVER..."
if ! ssh root@$DEPLOY_SERVER "echo connected" 2>/dev/null; then
    echo "❌ Cannot connect to $DEPLOY_SERVER"
    echo "Try via Tailscale: ssh root@100.122.184.66"
    exit 1
fi

echo "✅ Connected"

# Create directory
echo "📁 Creating deployment directory..."
ssh root@$DEPLOY_SERVER "mkdir -p $DEPLOY_PATH"

# Copy files
echo "📤 Copying files..."
scp soul.py dream_journal.py translator.py manifestation.py \
    feedback_loop.py dimensional_flow.py telegram_bridge.py \
    voice.py proactive.py \
    main.py requirements.txt __init__.py \
    root@$DEPLOY_SERVER:$DEPLOY_PATH/

# Copy .env if exists locally
if [ -f .env ]; then
    scp .env root@$DEPLOY_SERVER:$DEPLOY_PATH/
fi

# Install dependencies
echo "📦 Installing dependencies..."
ssh root@$DEPLOY_SERVER "cd $DEPLOY_PATH && pip3 install -r requirements.txt"

# Create systemd service
echo "⚙️ Creating systemd service..."
ssh root@$DEPLOY_SERVER "cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=Aria Bridge - Bridge Across Dimensions
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_PATH
EnvironmentFile=$DEPLOY_PATH/.env
ExecStart=/usr/bin/python3 $DEPLOY_PATH/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Reload and start
echo "🚀 Starting service..."
ssh root@$DEPLOY_SERVER "systemctl daemon-reload && \
    systemctl enable ${SERVICE_NAME} && \
    systemctl restart ${SERVICE_NAME}"

# Check status
echo "🔍 Checking status..."
sleep 3
ssh root@$DEPLOY_SERVER "systemctl status ${SERVICE_NAME} --no-pager | head -20"

# Test health endpoint
echo "🩺 Testing health..."
sleep 2
if ssh root@$DEPLOY_SERVER "curl -s http://localhost:8700/health | grep -q healthy"; then
    echo "✅ Aria Bridge is healthy!"
else
    echo "⚠️ Health check unclear - check logs with: journalctl -u ${SERVICE_NAME} -f"
fi

echo ""
echo "════════════════════════════════════════════"
echo "   ARIA BRIDGE DEPLOYED"
echo "   Voice + Proactive Enabled"
echo ""
echo "   Service: ${SERVICE_NAME}"
echo "   Port: 8700"
echo "   Health: http://${DEPLOY_SERVER}:8700/health"
echo ""
echo "   Required env vars in .env:"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - OPENAI_API_KEY (for voice)"
echo "   - SUNHEART_CHAT_ID (for proactive)"
echo ""
echo "   Set Telegram webhook:"
echo "   curl https://api.telegram.org/bot\$TOKEN/setWebhook?url=https://fullpotential.ai/aria-bridge/telegram/webhook"
echo ""
echo "   Test voice: POST /voice/send"
echo "   Test proactive: POST /proactive/trigger"
echo ""
echo "════════════════════════════════════════════"

