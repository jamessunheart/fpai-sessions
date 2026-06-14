#!/usr/bin/env bash
# deploy.sh — deploy legal-critic to brain server (162.0.208.88)
set -euo pipefail

REMOTE_HOST="${LEGAL_CRITIC_HOST:-root@162.0.208.88}"
REMOTE_DIR="${LEGAL_CRITIC_DIR:-/opt/legal-critic}"
SERVICE_NAME="legal-critic"
PORT=28092

echo "→ rsync code to $REMOTE_HOST:$REMOTE_DIR"
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR/system-prompts $REMOTE_DIR/scripts"
rsync -avz --delete \
  --exclude=.venv --exclude=__pycache__ --exclude=*.pyc \
  ./app.py ./requirements.txt \
  "$REMOTE_HOST:$REMOTE_DIR/"
rsync -avz ./system-prompts/ "$REMOTE_HOST:$REMOTE_DIR/system-prompts/"
rsync -avz ./scripts/ "$REMOTE_HOST:$REMOTE_DIR/scripts/"

echo "→ install venv + deps"
ssh "$REMOTE_HOST" "set -e; cd $REMOTE_DIR
  test -d .venv || python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements.txt"

echo "→ ensure systemd unit"
ssh "$REMOTE_HOST" "cat > /etc/systemd/system/${SERVICE_NAME}.service <<'EOF'
[Unit]
Description=legal-critic — The Counsel (RAG over Sunheart legal corpus + Claude)
After=network.target sh-brain-index.service
Wants=sh-brain-index.service

[Service]
Type=simple
User=root
WorkingDirectory=$REMOTE_DIR
EnvironmentFile=/etc/legal-critic/legal-critic.env
ExecStart=$REMOTE_DIR/.venv/bin/uvicorn app:app --host 127.0.0.1 --port $PORT --log-level info
Restart=on-failure
RestartSec=3
StandardOutput=append:/var/log/legal-critic.log
StandardError=append:/var/log/legal-critic.log

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}
sleep 2
systemctl status ${SERVICE_NAME} --no-pager | head -10"

echo "→ check /healthz"
ssh "$REMOTE_HOST" "curl -sf http://127.0.0.1:$PORT/healthz || echo 'health check failed'"

echo "→ done"
