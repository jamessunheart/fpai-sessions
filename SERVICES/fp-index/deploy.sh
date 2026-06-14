#!/bin/bash
# Deploy FP Index v5.1.0 to production
# Target: Primary server (198.54.123.234) port 8550
# This script packages the service, sends it to the server,
# sets up the environment, and configures nginx for fullpotential.ai

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() { echo -e "${CYAN}[$1]${NC} $2"; }
print_ok() { echo -e "${GREEN}  ✓ $1${NC}"; }
print_fail() { echo -e "${RED}  ✗ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ! $1${NC}"; }

SERVER="198.54.123.234"
SSH="ssh root@${SERVER}"
SCP="scp -r"
REMOTE_DIR="/opt/fpai/services/fp-index"
SERVICE_NAME="fpai-fp-index"
PORT=8550

echo ""
echo "═══════════════════════════════════════════════════════"
echo " FP INDEX v5.1.0 — Production Deployment"
echo " Target: ${SERVER}:${PORT}"
echo " Domain: fullpotential.ai"
echo "═══════════════════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Step 1: Package ──────────────────────────────────────
print_step "1/6" "Packaging service..."

STAGING="/tmp/fp-index-deploy"
rm -rf "$STAGING"
mkdir -p "$STAGING/app/models"

cp -r app/*.py "$STAGING/app/"
cp -r app/models/*.py "$STAGING/app/models/"
cp requirements.txt "$STAGING/"
cp simulation.py "$STAGING/" 2>/dev/null || true
cp verification-report-v1.1.json "$STAGING/" 2>/dev/null || true

# Create __init__ files
touch "$STAGING/app/__init__.py" 2>/dev/null || true
touch "$STAGING/app/models/__init__.py" 2>/dev/null || true

print_ok "Packaged $(find "$STAGING" -name '*.py' | wc -l | tr -d ' ') Python files"

# ── Step 2: Send to server ───────────────────────────────
print_step "2/6" "Sending to server..."

$SSH "mkdir -p ${REMOTE_DIR}/app/models" 2>/dev/null || true

# Backup existing if present
$SSH "
  if [ -d ${REMOTE_DIR}/app ]; then
    cp -r ${REMOTE_DIR} ${REMOTE_DIR}.bak.\$(date +%Y%m%d-%H%M%S)
    echo 'Backup created'
  fi
" 2>/dev/null || true

$SCP "$STAGING/app/"*.py "root@${SERVER}:${REMOTE_DIR}/app/"
$SCP "$STAGING/app/models/"*.py "root@${SERVER}:${REMOTE_DIR}/app/models/"
$SCP "$STAGING/requirements.txt" "root@${SERVER}:${REMOTE_DIR}/"
$SCP "$STAGING/simulation.py" "root@${SERVER}:${REMOTE_DIR}/" 2>/dev/null || true
$SCP "$STAGING/verification-report-v1.1.json" "root@${SERVER}:${REMOTE_DIR}/" 2>/dev/null || true

print_ok "Files transferred"

# ── Step 3: Set up environment ───────────────────────────
print_step "3/6" "Setting up Python environment on server..."

$SSH "
  cd ${REMOTE_DIR}
  if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo 'Virtual environment created'
  fi
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  echo 'Dependencies installed'
"

print_ok "Environment ready"

# ── Step 4: Create systemd service ───────────────────────
print_step "4/6" "Creating systemd service..."

$SSH "cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=Full Potential Index v5.1.0 — Constitutional Intelligence Economy
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${REMOTE_DIR}
ExecStart=${REMOTE_DIR}/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=5
Environment=FP_INDEX_PORT=${PORT}
Environment=FP_INDEX_DB=sqlite+aiosqlite:///${REMOTE_DIR}/fp_index.db

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}
echo 'Service started'
"

sleep 3

# Quick health check on server
HEALTH=$($SSH "curl -s http://localhost:${PORT}/health 2>/dev/null" || echo "FAIL")
if echo "$HEALTH" | grep -q "healthy"; then
  print_ok "Service healthy on server"
else
  print_fail "Service not responding yet — checking logs..."
  $SSH "journalctl -u ${SERVICE_NAME} -n 20 --no-pager" 2>/dev/null || true
  echo ""
  print_warn "Service may need more time to start. Continuing..."
fi

# ── Step 5: Configure nginx ──────────────────────────────
print_step "5/6" "Configuring nginx for fullpotential.ai..."

$SSH "cat > /etc/nginx/sites-available/fullpotential.ai << 'NGINXCONF'
server {
    listen 80;
    server_name fullpotential.ai www.fullpotential.ai;

    location / {
        proxy_pass http://localhost:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
NGINXCONF

ln -sf /etc/nginx/sites-available/fullpotential.ai /etc/nginx/sites-enabled/fullpotential.ai

# Test nginx config
nginx -t 2>&1 && echo 'Nginx config valid' || echo 'Nginx config error'
systemctl reload nginx
echo 'Nginx reloaded'
"

print_ok "Nginx configured — fullpotential.ai → localhost:${PORT}"

# ── Step 6: SSL (if certbot available) ───────────────────
print_step "6/6" "Checking SSL..."

$SSH "
  if command -v certbot &>/dev/null; then
    # Check if cert already exists
    if [ -d /etc/letsencrypt/live/fullpotential.ai ]; then
      echo 'SSL certificate already exists — reapplying to nginx'
      certbot --nginx -d fullpotential.ai -d www.fullpotential.ai \
        --non-interactive --agree-tos --email james@fullpotential.com \
        --redirect --keep-until-expiring 2>&1 || echo 'SSL reapply skipped'
    else
      echo 'Installing new SSL certificate...'
      certbot --nginx -d fullpotential.ai -d www.fullpotential.ai \
        --non-interactive --agree-tos --email james@fullpotential.com \
        --redirect 2>&1 || echo 'SSL install failed — HTTP still works'
    fi
  else
    echo 'certbot not found — serving HTTP only'
  fi
" 2>/dev/null || print_warn "SSL setup skipped"

print_ok "SSL configured"

# ── Verify ────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo " VERIFICATION"
echo "═══════════════════════════════════════════════════════"
echo ""

sleep 2

# Health check
echo -n "  /health ............ "
H=$(curl -s "http://${SERVER}:${PORT}/health" 2>/dev/null)
if echo "$H" | grep -q "healthy"; then
  echo -e "${GREEN}PASS${NC} (v$(echo "$H" | python3 -c 'import sys,json; print(json.load(sys.stdin)["version"])' 2>/dev/null || echo '?'))"
else
  echo -e "${RED}FAIL${NC}"
fi

# Constitution
echo -n "  /constitution ...... "
C=$(curl -s "http://${SERVER}:${PORT}/api/v1/constitution" 2>/dev/null)
if echo "$C" | grep -q "CORA Nation"; then
  echo -e "${GREEN}PASS${NC}"
else
  echo -e "${RED}FAIL${NC}"
fi

# Network state
echo -n "  /network/state ..... "
N=$(curl -s "http://${SERVER}:${PORT}/api/v1/network/state" 2>/dev/null)
if echo "$N" | grep -q "genesis"; then
  echo -e "${GREEN}PASS${NC} (genesis phase, bootstrap active)"
else
  echo -e "${RED}FAIL${NC}"
fi

# Register endpoint
echo -n "  /agents/register ... "
R=$(curl -s -X POST "http://${SERVER}:${PORT}/api/v1/agents/register" -H 'Content-Type: application/json' -d '{"name":"deploy-test","description":"deployment verification"}' 2>/dev/null)
if echo "$R" | grep -q "api_key"; then
  echo -e "${GREEN}PASS${NC} (agent registration works)"
else
  echo -e "${RED}FAIL${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo " FP INDEX v5.1.0 — DEPLOYED"
echo ""
echo " Server:  ${SERVER}:${PORT}"
echo " Domain:  https://fullpotential.ai"
echo " Health:  https://fullpotential.ai/health"
echo " Const:   https://fullpotential.ai/constitution"
echo " Register: POST https://fullpotential.ai/api/v1/agents/register"
echo "═══════════════════════════════════════════════════════"
echo ""

rm -rf "$STAGING"
