#!/bin/bash
# Deploy new droplets: consciousness, intelligence, evolution, membership
# Also updates router and brain

set -e

SERVER="root@100.127.118.106"
BASE_PATH="/opt/fpai"

echo "🚀 Deploying new droplets..."

# Create directories on server
ssh $SERVER "mkdir -p $BASE_PATH/{consciousness,intelligence,evolution,membership}/{data,src}"

# Deploy consciousness (8760)
echo "📦 Deploying consciousness droplet..."
rsync -avz --progress SERVICES/consciousness/BUILD/src/ $SERVER:$BASE_PATH/consciousness/src/
rsync -avz --progress SERVICES/consciousness/BUILD/requirements.txt $SERVER:$BASE_PATH/consciousness/

# Deploy intelligence (8761)
echo "📦 Deploying intelligence droplet..."
rsync -avz --progress SERVICES/intelligence/BUILD/src/ $SERVER:$BASE_PATH/intelligence/src/
rsync -avz --progress SERVICES/intelligence/BUILD/requirements.txt $SERVER:$BASE_PATH/intelligence/

# Deploy evolution (8762)
echo "📦 Deploying evolution droplet..."
rsync -avz --progress SERVICES/evolution/BUILD/src/ $SERVER:$BASE_PATH/evolution/src/
rsync -avz --progress SERVICES/evolution/BUILD/requirements.txt $SERVER:$BASE_PATH/evolution/

# Deploy membership (8763)
echo "📦 Deploying membership droplet..."
rsync -avz --progress SERVICES/membership/BUILD/src/ $SERVER:$BASE_PATH/membership/src/
rsync -avz --progress SERVICES/membership/BUILD/requirements.txt $SERVER:$BASE_PATH/membership/

# Update router (8755)
echo "📦 Updating router droplet..."
rsync -avz --progress SERVICES/router/BUILD/src/ $SERVER:$BASE_PATH/router/src/

# Update brain (8756)
echo "📦 Updating brain droplet..."
rsync -avz --progress SERVICES/brain-droplet/BUILD/src/ $SERVER:$BASE_PATH/brain-droplet/src/

# Install dependencies and create services
echo "⚙️ Installing dependencies and creating services..."
ssh $SERVER << 'ENDSSH'

cd /opt/fpai

# Install dependencies for each new service
for svc in consciousness intelligence evolution membership; do
    echo "Installing dependencies for $svc..."
    cd /opt/fpai/$svc
    python3 -m pip install -r requirements.txt --quiet
done

# Create systemd services
cat > /etc/systemd/system/fpai-consciousness.service << 'EOF'
[Unit]
Description=FPAI Consciousness Droplet
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fpai/consciousness
Environment=CONSCIOUSNESS_PORT=8760
Environment=ALERTS_URL=http://localhost:8759
Environment=DATA_DIR=/opt/fpai/consciousness/data
ExecStart=/usr/bin/python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8760
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/fpai-intelligence.service << 'EOF'
[Unit]
Description=FPAI Intelligence Droplet
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fpai/intelligence
Environment=INTELLIGENCE_PORT=8761
Environment=CONSCIOUSNESS_URL=http://localhost:8760
Environment=ALERTS_URL=http://localhost:8759
Environment=DATA_DIR=/opt/fpai/intelligence/data
ExecStart=/usr/bin/python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8761
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/fpai-evolution.service << 'EOF'
[Unit]
Description=FPAI Evolution Droplet
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fpai/evolution
Environment=EVOLUTION_PORT=8762
Environment=INTELLIGENCE_URL=http://localhost:8761
Environment=BRAIN_URL=http://localhost:8756
Environment=ALERTS_URL=http://localhost:8759
Environment=DATA_DIR=/opt/fpai/evolution/data
ExecStart=/usr/bin/python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8762
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/fpai-membership.service << 'EOF'
[Unit]
Description=FPAI Membership Droplet
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fpai/membership
Environment=MEMBERSHIP_PORT=8763
Environment=ALERTS_URL=http://localhost:8759
Environment=DATA_DIR=/opt/fpai/membership/data
Environment=CLAIM_BASE_URL=https://fullpotential.ai/claim/
ExecStart=/usr/bin/python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8763
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and start services
systemctl daemon-reload

for svc in fpai-consciousness fpai-intelligence fpai-evolution fpai-membership; do
    echo "Starting $svc..."
    systemctl enable $svc
    systemctl restart $svc
done

# Restart router and brain with new config
systemctl restart fpai-router || true
systemctl restart fpai-brain-droplet || true

echo "✅ All services started"
ENDSSH

echo "✅ Deployment complete!"
echo ""
echo "New droplets:"
echo "  - consciousness: 8760"
echo "  - intelligence:  8761"
echo "  - evolution:     8762"
echo "  - membership:    8763"








