#!/bin/bash
# Deployment script for Full Potential AI Voice Interface

SERVER_IP="64.23.188.18"
SERVER_USER="root"
APP_DIR="/opt/full-potential-ai"

echo "🚀 Deploying to server..."

# 1. Install Python and dependencies
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
apt-get update
apt-get install -y python3 python3-pip git
pip3 install --upgrade pip
ENDSSH

# 2. Create app directory
ssh $SERVER_USER@$SERVER_IP "mkdir -p $APP_DIR"

# 3. Copy files
scp -r ./* $SERVER_USER@$SERVER_IP:$APP_DIR/

# 4. Install Python dependencies
ssh $SERVER_USER@$SERVER_IP << ENDSSH
cd $APP_DIR
pip3 install -r requirements.txt
ENDSSH

# 5. Create systemd service
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cat > /etc/systemd/system/full-potential-ai.service << EOF
[Unit]
Description=Full Potential AI Voice Interface
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/full-potential-ai
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 -m chainlit run app.py --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable full-potential-ai
systemctl start full-potential-ai
ENDSSH

# 6. Configure firewall
ssh $SERVER_USER@$SERVER_IP "ufw allow 8000/tcp"

echo "✅ Deployment complete!"
echo "Access your app at: http://$SERVER_IP:8000"

