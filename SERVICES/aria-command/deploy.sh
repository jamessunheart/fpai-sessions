#!/bin/bash
# ============================================================================
# ARIA COMMAND CENTER DEPLOYMENT
# ============================================================================

set -e

SERVICE_NAME="aria-command"
SERVICE_DIR="/opt/fpai/${SERVICE_NAME}"
LOCAL_DIR="$(dirname "$0")"

echo "=========================================="
echo "  DEPLOYING ARIA COMMAND CENTER"
echo "=========================================="

# ============================================================================
# 1. COPY FILES
# ============================================================================
echo ""
echo "📦 Copying files to ${SERVICE_DIR}..."

ssh root@162.0.208.88 "mkdir -p ${SERVICE_DIR}"
scp -r ${LOCAL_DIR}/* root@162.0.208.88:${SERVICE_DIR}/

echo "   ✅ Files copied"

# ============================================================================
# 2. INSTALL DEPENDENCIES
# ============================================================================
echo ""
echo "📚 Installing dependencies..."

ssh root@162.0.208.88 "cd ${SERVICE_DIR} && pip3 install -r requirements.txt"

echo "   ✅ Dependencies installed"

# ============================================================================
# 3. CREATE ENV FILE
# ============================================================================
echo ""
echo "🔐 Configuring environment..."

ssh root@162.0.208.88 "cat > ${SERVICE_DIR}/.env << 'EOF'
# Aria Command Center Environment

# Telegram
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
SUNHEART_CHAT_ID=${SUNHEART_CHAT_ID}

# AI APIs
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}

# GitHub
GITHUB_TOKEN=${GITHUB_TOKEN}
GITHUB_ORG=fullpotential-ai

# Service Config
ARIA_COMMAND_PORT=8750
FPAI_WORKSPACE=/Users/jamessunheart/FPAI_Cockpit
ARIA_STATE_DIR=/opt/fpai/aria-command/state
EOF"

ssh root@162.0.208.88 "mkdir -p /opt/fpai/aria-command/state"

echo "   ✅ Environment configured"

# ============================================================================
# 4. CREATE SYSTEMD SERVICE
# ============================================================================
echo ""
echo "⚙️  Creating systemd service..."

ssh root@162.0.208.88 "cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=Aria Command Center
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/aria-command
EnvironmentFile=/opt/fpai/aria-command/.env
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

echo "   ✅ Systemd service created"

# ============================================================================
# 5. START SERVICE
# ============================================================================
echo ""
echo "🚀 Starting service..."

ssh root@162.0.208.88 "systemctl daemon-reload && systemctl enable ${SERVICE_NAME} && systemctl restart ${SERVICE_NAME}"

sleep 3

# Check if running
STATUS=$(ssh root@162.0.208.88 "systemctl is-active ${SERVICE_NAME}" 2>/dev/null || echo "failed")

if [ "$STATUS" = "active" ]; then
    echo "   ✅ Service is running"
else
    echo "   ❌ Service failed to start"
    ssh root@162.0.208.88 "journalctl -u ${SERVICE_NAME} --no-pager -n 20"
    exit 1
fi

# ============================================================================
# 6. UPDATE TELEGRAM WEBHOOK
# ============================================================================
echo ""
echo "🔗 Updating Telegram webhook..."

# The webhook should point to the main Aria service which will forward to command center
# This is handled by the existing nginx config

echo "   ✅ Webhook configured (uses existing Aria webhook)"

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "=========================================="
echo "  DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Service: ${SERVICE_NAME}"
echo "Port: 8750"
echo "Status: $(ssh root@162.0.208.88 "systemctl is-active ${SERVICE_NAME}")"
echo ""
echo "Endpoints:"
echo "  GET  /health         - Health check"
echo "  GET  /status         - Full status"
echo "  POST /telegram/webhook - Telegram webhook"
echo "  GET  /files/read     - Read files"
echo "  POST /files/write    - Write files"
echo "  POST /terminal/run   - Run commands"
echo "  GET  /git/status     - Git status"
echo "  GET  /trading/*      - Trading info"
echo "  GET  /agents         - Agent registry"
echo ""
echo "Commands (via Telegram):"
echo "  /status   - System status"
echo "  /health   - Health check"
echo "  /brief    - Daily briefing (voice)"
echo "  /positions - Trading positions"
echo "  /signals  - Active signals"
echo "  /run      - Execute commands"
echo "  /read     - Read files"
echo "  /search   - Search code"
echo "  /git      - Git operations"
echo "  /build    - Create builds"
echo "  /pending  - Pending changes"
echo "  /approve  - Approve changes"
echo "  /agents   - Agent status"
echo "  /help     - Show all commands"
echo ""
echo "Voice: Send voice messages for hands-free control!"
echo "=========================================="


