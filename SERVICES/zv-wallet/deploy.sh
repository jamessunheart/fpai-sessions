#!/usr/bin/env bash
# Deploy zv-wallet to 198.54.123.234 (idempotent)
set -euo pipefail

HOST="${ZV_WALLET_HOST:-root@198.54.123.234}"
REMOTE="/opt/zv-wallet/app"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[deploy] syncing to $HOST:$REMOTE"
ssh "$HOST" "mkdir -p $REMOTE /var/lib/zv-wallet/media"
rsync -az --delete --exclude '__pycache__' --exclude '.venv' \
  "$LOCAL_DIR/app/" "$HOST:$REMOTE/app/"
rsync -az --delete \
  "$LOCAL_DIR/dashboard/" "$HOST:$REMOTE/dashboard/"
rsync -az "$LOCAL_DIR/requirements.txt" "$HOST:$REMOTE/"
scp "$LOCAL_DIR/zv-wallet.service" "$HOST:/etc/systemd/system/zv-wallet.service"

ssh "$HOST" "set -e
  cd $REMOTE
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  ./.venv/bin/pip install --quiet -r requirements.txt
  # Bootstrap env file if not present
  if [ ! -f /etc/zv-wallet.env ]; then
    echo \"ZV_WALLET_ADMIN_TOKEN=$(openssl rand -hex 24)\" > /etc/zv-wallet.env
    echo \"EVO_BASE_URL=http://127.0.0.1:8081\" >> /etc/zv-wallet.env
    echo \"EVO_INSTANCE=zv-wallet\" >> /etc/zv-wallet.env
    EVO_KEY=\$(grep '^EVO_KEY=' /etc/zv-wallet.env | cut -d= -f2)
    if [ -z \"\$EVO_KEY\" ] && [ -f /opt/zv-wallet/evolution-api/.env ]; then
      EVO_KEY=\$(grep '^AUTHENTICATION_API_KEY=' /opt/zv-wallet/evolution-api/.env | cut -d= -f2)
      echo \"EVO_API_KEY=\$EVO_KEY\" >> /etc/zv-wallet.env
    fi
  fi
  systemctl daemon-reload
  systemctl enable zv-wallet.service
  systemctl restart zv-wallet.service
  sleep 2
  systemctl is-active zv-wallet.service
  curl -s http://127.0.0.1:8774/health | head -c 400
"

echo
echo "[deploy] done. Service active on 127.0.0.1:8774"
