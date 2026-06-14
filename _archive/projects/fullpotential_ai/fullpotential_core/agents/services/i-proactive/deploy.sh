#!/bin/bash

# Deploy I PROACTIVE to production server

set -e

SERVER="198.54.123.234"
SERVER_USER="root"
DEPLOY_PATH="/opt/fpai/i-proactive"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DEPLOYING I PROACTIVE TO SERVER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create deployment directory on server
echo "📁 Creating deployment directory..."
ssh ${SERVER_USER}@${SERVER} "mkdir -p ${DEPLOY_PATH}"

# Copy all files
echo "📤 Uploading files..."
scp -r app/ ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp -r config/ ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp requirements.txt ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp .env.example ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp Dockerfile ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/

# Setup and start service
echo "⚙️  Setting up service..."
ssh ${SERVER_USER}@${SERVER} << 'ENDSSH'

cd /opt/fpai/i-proactive

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env if doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit /opt/fpai/i-proactive/.env and add API keys"
fi

# Create systemd service
cat > /etc/systemd/system/i-proactive.service << 'EOF'
[Unit]
Description=I PROACTIVE - Central AI Orchestration Brick
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/i-proactive
Environment="PATH=/opt/fpai/i-proactive/venv/bin"
ExecStart=/opt/fpai/i-proactive/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8400
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
echo "1. Add your AI model API keys:"
echo "   nano /opt/fpai/i-proactive/.env"
echo "   (Add ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY)"
echo ""
echo "2. Start the service:"
echo "   systemctl start i-proactive"
echo "   systemctl enable i-proactive"
echo ""
echo "3. Check status:"
echo "   systemctl status i-proactive"
echo "   curl http://localhost:8400/health"
echo ""
echo "4. Test the service:"
echo "   curl http://198.54.123.234:8400/capabilities"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ENDSSH

echo ""
echo "✅ I PROACTIVE deployed to server!"
echo ""
echo "Service will run at: http://198.54.123.234:8400"
echo ""
