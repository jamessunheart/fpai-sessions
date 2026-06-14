#!/bin/bash

# Deploy I MATCH to production server

set -e

SERVER="198.54.123.234"
SERVER_USER="root"
DEPLOY_PATH="/opt/fpai/i-match"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DEPLOYING I MATCH TO SERVER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create deployment directory
echo "📁 Creating deployment directory..."
ssh ${SERVER_USER}@${SERVER} "mkdir -p ${DEPLOY_PATH}"

# Copy files
echo "📤 Uploading files..."
scp -r app/ ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp requirements.txt ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp .env.example ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/
scp Dockerfile ${SERVER_USER}@${SERVER}:${DEPLOY_PATH}/

# Setup service
echo "⚙️  Setting up service..."
ssh ${SERVER_USER}@${SERVER} << 'ENDSSH'

cd /opt/fpai/i-match

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env if doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit /opt/fpai/i-match/.env and add ANTHROPIC_API_KEY"
fi

# Create systemd service
cat > /etc/systemd/system/i-match.service << 'EOF'
[Unit]
Description=I MATCH - AI-Powered Matching Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/i-match
Environment="PATH=/opt/fpai/i-match/venv/bin"
ExecStart=/opt/fpai/i-match/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8401
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
echo "1. Add API key: nano /opt/fpai/i-match/.env"
echo "2. Start service: systemctl start i-match"
echo "3. Enable on boot: systemctl enable i-match"
echo "4. Check status: systemctl status i-match"
echo "5. Test: curl http://198.54.123.234:8401/health"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ENDSSH

echo ""
echo "✅ I MATCH deployed!"
echo "Service: http://198.54.123.234:8401"
echo ""
