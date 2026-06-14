# Deployment Instructions

## Quick Deploy (Manual Steps)

### 1. Connect to Server
```bash
ssh root@64.23.188.18
# Password: <OWNER_PROVIDED_PASSWORD>
```

### 2. On Server - Install Dependencies
```bash
apt-get update
apt-get install -y python3 python3-pip git
pip3 install --upgrade pip
```

### 3. Create App Directory
```bash
mkdir -p /opt/full-potential-ai
cd /opt/full-potential-ai
```

### 4. From Your Laptop - Copy Files
```bash
# From voice-interface directory
scp -r ./* root@64.23.188.18:/opt/full-potential-ai/
```

### 5. On Server - Install Python Dependencies
```bash
cd /opt/full-potential-ai
pip3 install -r requirements.txt
```

### 6. Create .env File on Server
```bash
nano .env
# Add: ANTHROPIC_API_KEY=sk-ant-api03-<INSERT_KEY_HERE>
```

### 7. Create Systemd Service
```bash
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
```

### 8. Configure Firewall
```bash
ufw allow 8000/tcp
```

### 9. Check Status
```bash
systemctl status full-potential-ai
```

## Access Your App
http://64.23.188.18:8000

