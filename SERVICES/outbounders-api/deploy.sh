#!/usr/bin/env bash
# Deploy Outbounders Agent API v0 to 209.74.93.72:/opt/outbounders-api/
# Idempotent — safe to re-run. Does NOT touch Apache config (prints instructions).
set -euo pipefail

SERVER="root@209.74.93.72"
REMOTE_DIR="/opt/outbounders-api"
SERVICE="outbounders-api"
PORT=8300
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/6] Sync code to ${SERVER}:${REMOTE_DIR}"
ssh "$SERVER" "mkdir -p ${REMOTE_DIR}"
rsync -az --delete \
  --exclude venv --exclude __pycache__ --exclude '.DS_Store' \
  "${LOCAL_DIR}/" "${SERVER}:${REMOTE_DIR}/"

echo "==> [2/6] Create venv + install deps"
ssh "$SERVER" bash -s <<EOF
set -euo pipefail
cd ${REMOTE_DIR}
if [ ! -d venv ]; then python3 -m venv venv; fi
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet fastapi 'uvicorn[standard]' pymysql
EOF

echo "==> [3/6] Run migration (idempotent)"
ssh "$SERVER" "mysql obapp_outbounders < ${REMOTE_DIR}/migrations/001_api_keys.sql"

echo "==> [4/6] Install systemd unit"
ssh "$SERVER" bash -s <<EOF
set -euo pipefail
cat > /etc/systemd/system/${SERVICE}.service <<'UNIT'
[Unit]
Description=Outbounders Agent API (FastAPI sidecar)
After=network.target mariadb.service mysql.service

[Service]
Type=simple
WorkingDirectory=${REMOTE_DIR}
Environment=DB_NAME=obapp_outbounders
# Socket auth as root via /root/.my.cnf by default.
# For a dedicated DB user instead, set: DB_USER=... DB_PASS=... DB_HOST=localhost
ExecStart=${REMOTE_DIR}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable ${SERVICE}
systemctl restart ${SERVICE}
EOF

echo "==> [5/6] Health check"
sleep 2
ssh "$SERVER" "curl -sf http://127.0.0.1:${PORT}/v1/health" && echo "" \
  || { echo "HEALTH CHECK FAILED — journalctl -u ${SERVICE} -n 50"; exit 1; }

echo "==> [6/6] Apache/cPanel proxy — MANUAL STEP (not auto-applied)"
cat <<'APACHE'
------------------------------------------------------------------------
To expose api.outbounders.com, add this vhost include (cPanel: place in
/etc/apache2/conf.d/userdata/ssl/2_4/outbndrs/api.outbounders.com/proxy.conf
after creating the api subdomain in cPanel, then rebuild+restart httpd):

    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8300/
    ProxyPassReverse / http://127.0.0.1:8300/

Then:
    /scripts/rebuildhttpdconf && systemctl restart httpd

DNS: add A record api.outbounders.com -> 209.74.93.72 (self-hosted
ns1/ns2.outbounders.com — no Cloudflare on this domain).
------------------------------------------------------------------------
APACHE

echo "Deploy complete. Service: ${SERVICE} on 127.0.0.1:${PORT}"
