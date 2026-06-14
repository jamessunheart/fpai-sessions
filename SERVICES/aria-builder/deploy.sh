#!/bin/bash
# ============================================================================
# ARIA BUILDER DEPLOYMENT SCRIPT
# ============================================================================
# Deploys the Aria Builder service to the secondary server
#
# Usage:
#   ./deploy.sh
#
# This script:
# 1. Copies files to server
# 2. Installs dependencies
# 3. Configures environment
# 4. Creates systemd service
# 5. Starts the service

set -e

# Configuration
SERVER="162.0.208.88"
USER="root"
DEPLOY_PATH="/opt/fpai/aria-builder"
SERVICE_NAME="aria-builder"
PORT="8720"

echo "============================================"
echo "  ARIA BUILDER DEPLOYMENT"
echo "============================================"
echo ""

# Check SSH access
echo "1. Checking SSH access..."
if ! ssh -o ConnectTimeout=5 ${USER}@${SERVER} "echo 'SSH OK'" 2>/dev/null; then
    echo "❌ Cannot connect to ${SERVER}"
    exit 1
fi
echo "✅ SSH connection OK"

# Create directory
echo ""
echo "2. Creating deployment directory..."
ssh ${USER}@${SERVER} "mkdir -p ${DEPLOY_PATH}"
echo "✅ Directory created"

# Copy files
echo ""
echo "3. Copying files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
scp -r ${SCRIPT_DIR}/*.py ${USER}@${SERVER}:${DEPLOY_PATH}/
scp ${SCRIPT_DIR}/requirements.txt ${USER}@${SERVER}:${DEPLOY_PATH}/
echo "✅ Files copied"

# Install dependencies
echo ""
echo "4. Installing dependencies..."
ssh ${USER}@${SERVER} "cd ${DEPLOY_PATH} && pip3 install -r requirements.txt --quiet"
echo "✅ Dependencies installed"

# Configure environment
echo ""
echo "5. Configuring environment..."
ssh ${USER}@${SERVER} "cat > ${DEPLOY_PATH}/.env << 'EOF'
# Aria Builder Environment
TELEGRAM_BOT_TOKEN=\$(grep TELEGRAM_BOT_TOKEN /opt/fpai/aria/.env | cut -d= -f2)
OPENAI_API_KEY=\$(grep OPENAI_API_KEY /opt/fpai/aria/.env | cut -d= -f2)
ANTHROPIC_API_KEY=DISABLED_KEY_REMOVED  # rotated 2026-04-27; sub a fresh key before deploy
GEMINI_API_KEY=<REDACTED_GEMINI_KEY>
BUILDER_PORT=${PORT}
EOF"
echo "✅ Environment configured"

# Create systemd service
echo ""
echo "6. Creating systemd service..."
ssh ${USER}@${SERVER} "cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=Aria Builder Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${DEPLOY_PATH}
EnvironmentFile=${DEPLOY_PATH}/.env
ExecStart=/usr/bin/python3 ${DEPLOY_PATH}/api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"
echo "✅ Systemd service created"

# Reload and start
echo ""
echo "7. Starting service..."
ssh ${USER}@${SERVER} "systemctl daemon-reload"
ssh ${USER}@${SERVER} "systemctl enable ${SERVICE_NAME}"
ssh ${USER}@${SERVER} "systemctl restart ${SERVICE_NAME}"
echo "✅ Service started"

# Check status
echo ""
echo "8. Checking service status..."
sleep 2
if ssh ${USER}@${SERVER} "systemctl is-active ${SERVICE_NAME}" | grep -q "active"; then
    echo "✅ Service is running"
else
    echo "⚠️ Service may not be running. Check logs:"
    echo "   ssh ${USER}@${SERVER} journalctl -u ${SERVICE_NAME} -n 50"
fi

# Test endpoint
echo ""
echo "9. Testing endpoint..."
sleep 2
if curl -s "http://${SERVER}:${PORT}/health" | grep -q "healthy"; then
    echo "✅ API is responding"
else
    echo "⚠️ API may not be responding yet"
fi

echo ""
echo "============================================"
echo "  DEPLOYMENT COMPLETE"
echo "============================================"
echo ""
echo "Service URL: http://${SERVER}:${PORT}"
echo ""
echo "Test commands:"
echo "  curl http://${SERVER}:${PORT}/health"
echo "  curl http://${SERVER}:${PORT}/builder/status"
echo ""
echo "View logs:"
echo "  ssh ${USER}@${SERVER} journalctl -u ${SERVICE_NAME} -f"
echo ""


