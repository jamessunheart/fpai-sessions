#!/bin/bash

# 🚀 DEPLOY AUTONOMOUS EXECUTOR TO SERVER
# This makes everything autonomous - architect declares intent, system executes

set -e

SERVER="198.54.123.234"
SERVER_USER="root"
DEPLOY_PATH="/opt/fpai/autonomous-executor"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DEPLOYING AUTONOMOUS EXECUTOR TO SERVER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create deployment directory on server
echo "📁 Creating deployment directory..."
ssh ${SERVER_USER}@${SERVER} "mkdir -p ${DEPLOY_PATH}"

# Copy all files
echo "📤 Uploading files..."
scp -r app/ ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp requirements.txt ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp .env.example ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/

# Setup and start service
echo "⚙️  Setting up service..."
ssh ${SERVER_USER}@${SERVER} << 'ENDSSH'

cd /opt/fpai/autonomous-executor

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env if doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit /opt/fpai/autonomous-executor/.env and add ANTHROPIC_API_KEY"
fi

# Create systemd service
cat > /etc/systemd/system/autonomous-executor.service << 'EOF'
[Unit]
Description=Autonomous Executor - Enables True Self-Optimization
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/autonomous-executor
Environment="PATH=/opt/fpai/autonomous-executor/venv/bin"
ExecStart=/opt/fpai/autonomous-executor/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8400
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo ""
echo "✅ Deployment complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Add your Anthropic API key:"
echo "   nano /opt/fpai/autonomous-executor/.env"
echo "   (Change ANTHROPIC_API_KEY=your_api_key_here to your actual key)"
echo ""
echo "2. Start the service:"
echo "   systemctl start autonomous-executor"
echo "   systemctl enable autonomous-executor"
echo ""
echo "3. Check status:"
echo "   systemctl status autonomous-executor"
echo "   curl http://localhost:8400/executor/health"
echo ""
echo "4. Build your first service autonomously:"
echo "   curl -X POST http://localhost:8400/executor/build-droplet \\"
echo "     -d '{\"architect_intent\":\"Build I PROACTIVE\",\"droplet_id\":20}'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ENDSSH

echo ""
echo "✅ Autonomous Executor deployed to server!"
echo ""
echo "Service will run at: http://198.54.123.234:8400"
echo ""
