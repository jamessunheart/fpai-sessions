#!/usr/bin/env bash
# Deploy champion-sign webhook to primary server.
# Run from repo root: bash SERVICES/champion-sign/deploy.sh

set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SERVER="root@198.54.123.234"
REMOTE_DIR="/opt/fpai/services/champion-sign"
DATA_DIR="/var/lib/full-potential/champions"

echo "→ Creating remote directories..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  mkdir -p $REMOTE_DIR $DATA_DIR
  chown -R root:root $REMOTE_DIR $DATA_DIR
"

echo "→ Rsyncing service files..."
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  "$ROOT/SERVICES/champion-sign/main.py" \
  "$ROOT/SERVICES/champion-sign/requirements.txt" \
  "$ROOT/SERVICES/champion-sign/champion-sign.service" \
  "${SERVER}:${REMOTE_DIR}/"

echo "→ Setting up venv + installing deps..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  cd $REMOTE_DIR
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
  cp champion-sign.service /etc/systemd/system/champion-sign.service
  systemctl daemon-reload
  systemctl enable champion-sign
  systemctl restart champion-sign
  sleep 1
  systemctl is-active champion-sign && echo '   service active' || echo '   service not active'
"

echo "→ Health check..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "curl -s http://127.0.0.1:8771/health"

echo ""
echo "✅ Service deployed. Running on 127.0.0.1:8771."
echo ""
echo "Next: add nginx /api/champion/ proxy block (run nginx_install.sh)."
