#!/bin/bash
#
# Deploy All Droplets
# ==================
# Deploys all 6 UDC-compliant droplets to the server
#

set -e

SERVER="root@100.127.118.106"
REMOTE_BASE="/opt/fpai"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DROPLETS=("alerts" "memory-droplet" "brain-droplet" "trader" "router" "supervisor")

echo "========================================"
echo "  DEPLOYING ALL DROPLETS"
echo "========================================"
echo ""

for droplet in "${DROPLETS[@]}"; do
    echo -e "${YELLOW}Deploying $droplet...${NC}"
    
    LOCAL_PATH="$(dirname $0)/$droplet/BUILD"
    REMOTE_PATH="$REMOTE_BASE/$droplet"
    
    if [ ! -d "$LOCAL_PATH" ]; then
        echo -e "${RED}  $droplet BUILD directory not found, skipping${NC}"
        continue
    fi
    
    # Create remote directory
    ssh $SERVER "mkdir -p $REMOTE_PATH"
    
    # Sync files
    rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
        "$LOCAL_PATH/" "$SERVER:$REMOTE_PATH/"
    
    echo -e "${GREEN}  $droplet deployed${NC}"
done

echo ""
echo "========================================"
echo "  CREATING SYSTEMD SERVICES"
echo "========================================"
echo ""

# Create systemd service for each droplet
for droplet in "${DROPLETS[@]}"; do
    PORT=""
    case $droplet in
        "alerts") PORT=8765 ;;
        "memory-droplet") PORT=8753 ;;
        "brain-droplet") PORT=8752 ;;
        "trader") PORT=8751 ;;
        "router") PORT=8750 ;;
        "supervisor") PORT=8760 ;;
    esac
    
    SERVICE_NAME="${droplet}"
    
    echo -e "${YELLOW}Creating service: $SERVICE_NAME (port $PORT)${NC}"
    
    ssh $SERVER "cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=${droplet} Droplet
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fpai/${droplet}
ExecStart=/usr/bin/python3 src/main.py
Environment=PORT=${PORT}
Environment=PYTHONPATH=/opt/fpai/${droplet}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"
    
    echo -e "${GREEN}  Service created${NC}"
done

echo ""
echo "========================================"
echo "  INSTALLING DEPENDENCIES"
echo "========================================"
echo ""

for droplet in "${DROPLETS[@]}"; do
    echo -e "${YELLOW}Installing deps for $droplet...${NC}"
    ssh $SERVER "cd /opt/fpai/$droplet && pip3 install -r requirements.txt -q" || true
done

echo ""
echo "========================================"
echo "  RELOADING SYSTEMD"
echo "========================================"
echo ""

ssh $SERVER "systemctl daemon-reload"
echo -e "${GREEN}Systemd reloaded${NC}"

echo ""
echo "========================================"
echo "  DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "To start all droplets:"
echo "  ssh $SERVER 'for s in ${DROPLETS[*]}; do systemctl start \$s; done'"
echo ""
echo "To check status:"
echo "  ssh $SERVER 'for s in ${DROPLETS[*]}; do systemctl status \$s --no-pager | head -3; done'"








