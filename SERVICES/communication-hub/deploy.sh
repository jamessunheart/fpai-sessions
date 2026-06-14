#!/bin/bash
set -e

SERVICE_NAME="communication-hub"
SERVICE_DIR="/opt/fpai/services/$SERVICE_NAME"
PORT=8800

echo "Deploying $SERVICE_NAME..."

# 1. Create Directory
sudo mkdir -p $SERVICE_DIR
sudo chown -R $USER:$USER $SERVICE_DIR

# 2. Copy Files
cp -r * $SERVICE_DIR/

# 3. Setup Venv
cd $SERVICE_DIR
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# 4. Setup Systemd
sudo tee /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=FPAI Communication Hub
After=network.target

[Service]
User=root
WorkingDirectory=$SERVICE_DIR
ExecStart=$SERVICE_DIR/venv/bin/uvicorn app:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

# 5. Setup Nginx (Location Block)
# We append to the main Nginx config or a snippet if available.
# For now, we assume we can add a snippet or just rely on port forwarding if external access is needed.
# But let's add a snippet for /services/communication

sudo tee /etc/nginx/snippets/$SERVICE_NAME.conf <<EOF
location /services/communication/ {
    proxy_pass http://localhost:$PORT/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
EOF

# Check if we can include it in the main site. 
# Assuming /etc/nginx/sites-enabled/fullpotential exists and has 'include /etc/nginx/snippets/*.conf;' or similar.
# If not, we might need to add it manually.
# But for now, the service is running on 8800 locally.

echo "$SERVICE_NAME deployed on port $PORT"










