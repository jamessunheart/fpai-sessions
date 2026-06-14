#!/usr/bin/env bash
# deploy.sh — push apprentice-gateway to production and install systemd unit.
#
# Usage:  ./deploy.sh
# Assumes: SSH access to root@198.54.123.234, /etc/apprentice-gateway.env exists.

set -euo pipefail

SERVER=${SERVER:-root@198.54.123.234}
REMOTE_DIR=${REMOTE_DIR:-/opt/fpai/apps/apprentice-gateway}
LOCAL_DIR=$(cd "$(dirname "$0")" && pwd)

echo "Deploying apprentice-gateway → $SERVER:$REMOTE_DIR"

# 1. rsync app + static (skip venv, db, __pycache__)
rsync -avz --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.db' \
  --exclude '.env' \
  --exclude 'apprentice.db*' \
  "$LOCAL_DIR/" "$SERVER:$REMOTE_DIR/"

# 2. Install / refresh venv + deps
ssh "$SERVER" bash <<'EOF'
set -e
cd /opt/fpai/apps/apprentice-gateway
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt
mkdir -p /var/lib/apprentice-gateway
chmod 700 /var/lib/apprentice-gateway
EOF

# 3. Install systemd unit
scp "$LOCAL_DIR/apprentice-gateway.service" "$SERVER:/etc/systemd/system/fpai-apprentice-gateway.service"

# 4. Reload + start
ssh "$SERVER" bash <<'EOF'
set -e
systemctl daemon-reload
systemctl enable fpai-apprentice-gateway
systemctl restart fpai-apprentice-gateway
sleep 2
systemctl status fpai-apprentice-gateway --no-pager --lines 15
echo "---"
echo "Health check:"
curl -s http://127.0.0.1:8773/health | python3 -m json.tool
EOF

echo ""
echo "Deployed."
echo "Next: run setup_stripe.py on server to create products (idempotent):"
echo "  ssh $SERVER 'cd $REMOTE_DIR && STRIPE_SECRET_KEY=\$(grep STRIPE_SECRET_KEY /etc/apprentice-gateway.env|cut -d= -f2) .venv/bin/python -m app.setup_stripe'"
echo ""
echo "And register webhook in Stripe Dashboard → URL: https://fullpotential.com/apprentice/webhook"
