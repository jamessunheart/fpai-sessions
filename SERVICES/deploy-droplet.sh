#!/bin/bash
# =============================================================================
# DROPLET DEPLOYER - Deploy a single droplet to production
# =============================================================================
# Usage: ./deploy-droplet.sh <name> <port>
# Example: ./deploy-droplet.sh analytics 8764
# =============================================================================

set -e

# Configuration
REMOTE_HOST="${REMOTE_HOST:-root@100.127.118.106}"
SERVICES_DIR="/opt/fpai/SERVICES"
LOCAL_SERVICES="./SERVICES"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

NAME=$1
PORT=$2

if [ -z "$NAME" ] || [ -z "$PORT" ]; then
    echo -e "${RED}Usage: $0 <name> <port>${NC}"
    exit 1
fi

LOCAL_PATH="${LOCAL_SERVICES}/${NAME}"
REMOTE_PATH="${SERVICES_DIR}/${NAME}"

if [ ! -d "$LOCAL_PATH" ]; then
    echo -e "${RED}Error: ${LOCAL_PATH} does not exist. Run create-droplet.sh first.${NC}"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  DEPLOYING: ${NAME} → port ${PORT}                          ${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# =============================================================================
# Step 1: Validate locally
# =============================================================================
echo -e "\n${YELLOW}[1/6] Validating syntax...${NC}"
python3 -m py_compile "${LOCAL_PATH}/BUILD/src/main.py"
echo -e "${GREEN}✓ Syntax valid${NC}"

# =============================================================================
# Step 2: Create remote directory
# =============================================================================
echo -e "${YELLOW}[2/6] Creating remote directory...${NC}"
ssh "$REMOTE_HOST" "mkdir -p ${REMOTE_PATH}/BUILD/src ${REMOTE_PATH}/BUILD/tests"
echo -e "${GREEN}✓ Directory created${NC}"

# =============================================================================
# Step 3: Sync files
# =============================================================================
echo -e "${YELLOW}[3/6] Syncing files...${NC}"
rsync -avz --delete "${LOCAL_PATH}/BUILD/" "${REMOTE_HOST}:${REMOTE_PATH}/BUILD/"
echo -e "${GREEN}✓ Files synced${NC}"

# =============================================================================
# Step 4: Install dependencies
# =============================================================================
echo -e "${YELLOW}[4/6] Installing dependencies...${NC}"
ssh "$REMOTE_HOST" "cd ${REMOTE_PATH}/BUILD && pip install -r requirements.txt -q"
echo -e "${GREEN}✓ Dependencies installed${NC}"

# =============================================================================
# Step 5: Create/Update systemd service
# =============================================================================
echo -e "${YELLOW}[5/6] Creating systemd service...${NC}"
ssh "$REMOTE_HOST" "cat > /etc/systemd/system/fpai-${NAME}.service << EOF
[Unit]
Description=FPAI ${NAME} Droplet
After=network.target

[Service]
User=root
WorkingDirectory=${REMOTE_PATH}/BUILD
ExecStart=/usr/bin/python3 -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fpai-${NAME}

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable fpai-${NAME}.service"
echo -e "${GREEN}✓ Service created${NC}"

# =============================================================================
# Step 6: Start/Restart and verify
# =============================================================================
echo -e "${YELLOW}[6/6] Starting service...${NC}"

# Check if port is in use
PORT_PID=$(ssh "$REMOTE_HOST" "lsof -t -i:${PORT} 2>/dev/null || true")
if [ -n "$PORT_PID" ]; then
    echo -e "${YELLOW}Port ${PORT} in use by PID ${PORT_PID}, killing...${NC}"
    ssh "$REMOTE_HOST" "kill -9 ${PORT_PID} 2>/dev/null || true"
    sleep 2
fi

# Start service
ssh "$REMOTE_HOST" "systemctl restart fpai-${NAME}.service"
sleep 3

# Verify health
echo -e "${YELLOW}Verifying health...${NC}"
HEALTH=$(ssh "$REMOTE_HOST" "curl -s http://127.0.0.1:${PORT}/health 2>/dev/null || echo 'FAILED'")

if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Service healthy!${NC}"
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  ✅ DEPLOYMENT SUCCESSFUL                                  ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║  Service: fpai-${NAME}                                      "
    echo "║  Port: ${PORT}                                              "
    echo "║  Health: http://127.0.0.1:${PORT}/health                    "
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
else
    echo -e "${RED}✗ Service not healthy!${NC}"
    echo -e "${RED}Health response: ${HEALTH}${NC}"
    echo -e "${YELLOW}Check logs with: ssh $REMOTE_HOST 'journalctl -u fpai-${NAME} -n 50'${NC}"
    exit 1
fi

# =============================================================================
# Update supervisor config
# =============================================================================
echo -e "${YELLOW}Updating supervisor config...${NC}"
ssh "$REMOTE_HOST" "
if [ -f /opt/fpai/supervisor/droplet_config.json ]; then
    # Check if droplet already in config
    if ! grep -q '\"${NAME}\"' /opt/fpai/supervisor/droplet_config.json; then
        # Add to config using jq if available, otherwise manual
        if command -v jq &> /dev/null; then
            jq '.droplets += [{\"name\": \"${NAME}\", \"port\": ${PORT}, \"required\": false}]' /opt/fpai/supervisor/droplet_config.json > /tmp/droplet_config.json && mv /tmp/droplet_config.json /opt/fpai/supervisor/droplet_config.json
        fi
    fi
fi
"
echo -e "${GREEN}✓ Supervisor updated${NC}"

echo -e "\n${GREEN}Done! ${NAME} droplet is live on port ${PORT}${NC}"

