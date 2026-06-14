#!/bin/bash
# Deploy 2X Treasury to production server

echo "🚀 Deploying 2X Treasury to production..."

# Sync files to server
rsync -avz --exclude '__pycache__' --exclude '*.pyc' \
    /Users/jamessunheart/Development/SERVICES/2x-treasury/ \
    root@198.54.123.234:/root/SERVICES/2x-treasury/

# Create systemd service on server
ssh root@198.54.123.234 << 'REMOTE'
cd /root/SERVICES/2x-treasury

# Install dependencies
pip3 install -r requirements.txt

# Create systemd service
cat > /etc/systemd/system/2x-treasury.service << 'SERVICE'
[Unit]
Description=2X Treasury - SOL Investment System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/SERVICES/2x-treasury
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 8052
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Enable and start service
systemctl daemon-reload
systemctl enable 2x-treasury.service
systemctl restart 2x-treasury.service

echo "✅ 2X Treasury service deployed and started"
systemctl status 2x-treasury.service --no-pager

REMOTE

echo "✅ Deployment complete!"
echo "🌐 Access: http://198.54.123.234:8052"
