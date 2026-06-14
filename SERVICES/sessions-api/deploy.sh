#!/usr/bin/env bash
# Deploy sessions-api service.
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SERVER="root@198.54.123.234"
REMOTE_DIR="/opt/fpai/services/sessions-api"
DATA_DIR="/var/lib/full-potential/sessions"

# Generate token if absent
if [ ! -f "$HOME/.config/sessions-api.token" ]; then
  mkdir -p "$HOME/.config"
  python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$HOME/.config/sessions-api.token"
  chmod 600 "$HOME/.config/sessions-api.token"
  echo "→ Generated new SESSIONS_TOKEN at ~/.config/sessions-api.token"
fi
TOKEN="$(cat $HOME/.config/sessions-api.token)"

echo "→ Creating remote dirs..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  mkdir -p $REMOTE_DIR $DATA_DIR
  cat > /etc/sessions-api.env <<EOF
SESSIONS_TOKEN=$TOKEN
SESSIONS_DATA_DIR=$DATA_DIR
EOF
  chmod 600 /etc/sessions-api.env
"

echo "→ Rsyncing service files..."
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  "$ROOT/SERVICES/sessions-api/main.py" \
  "$ROOT/SERVICES/sessions-api/requirements.txt" \
  "$ROOT/SERVICES/sessions-api/sessions-api.service" \
  "${SERVER}:${REMOTE_DIR}/"

echo "→ Setup venv + systemd..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  cd $REMOTE_DIR
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
  cp sessions-api.service /etc/systemd/system/sessions-api.service
  systemctl daemon-reload
  systemctl enable sessions-api
  systemctl restart sessions-api
  sleep 1
  systemctl is-active sessions-api && echo '   service active' || echo '   service NOT active'
  curl -s http://127.0.0.1:8772/health
"
echo ""
echo "✅ sessions-api deployed at 127.0.0.1:8772"
echo ""
echo "Token at: ~/.config/sessions-api.token"
echo ""
echo "Next:"
echo "  - Add nginx /api/sessions/ proxy block"
echo "  - Use 'tools/session_state.py update' from any Claude session"
