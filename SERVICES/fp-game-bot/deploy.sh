#!/usr/bin/env bash
# Deploy fp-game-bot to primary server.
# Token must be passed via FPGAMEBOT_TOKEN env var or already in /etc/fp-game-bot/fp-game-bot.env on server.
#
# Usage:
#   FPGAMEBOT_TOKEN="123:ABC..." bash SERVICES/fp-game-bot/deploy.sh
# Or skip if token is already set on server:
#   bash SERVICES/fp-game-bot/deploy.sh

set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SERVER="root@198.54.123.234"
REMOTE_DIR="/opt/fpai/services/fp-game-bot"

echo "→ Creating remote dir + env file..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  mkdir -p $REMOTE_DIR /etc/fp-game-bot /var/lib/fp-game-bot
  if [ -n '${FPGAMEBOT_TOKEN:-}' ]; then
    cat > /etc/fp-game-bot/fp-game-bot.env <<EOF
TELEGRAM_BOT_TOKEN=${FPGAMEBOT_TOKEN}
CHAMPION_API_URL=https://fullpotential.com/api/champion
GAME_URL=https://fullpotential.com/game
LOG_LEVEL=INFO
EOF
    chmod 600 /etc/fp-game-bot/fp-game-bot.env
    echo '   wrote env file'
  else
    if [ ! -f /etc/fp-game-bot/fp-game-bot.env ]; then
      echo '   ⚠️  No token provided + no existing env file. Service will fail to start.'
    else
      echo '   env file already exists; not overwriting'
    fi
  fi
"

echo "→ Rsyncing service files..."
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  "$ROOT/SERVICES/fp-game-bot/main.py" \
  "$ROOT/SERVICES/fp-game-bot/requirements.txt" \
  "$ROOT/SERVICES/fp-game-bot/fp-game-bot.service" \
  "${SERVER}:${REMOTE_DIR}/"

echo "→ Setup venv + systemd..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  cd $REMOTE_DIR
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
  cp fp-game-bot.service /etc/systemd/system/fp-game-bot.service
  systemctl daemon-reload
  systemctl enable fp-game-bot
  systemctl restart fp-game-bot
  sleep 2
  systemctl is-active fp-game-bot && echo '   service active' || (echo '   service NOT active'; journalctl -u fp-game-bot -n 10 --no-pager)
"

echo ""
echo "✅ fp-game-bot deployed."
echo ""
echo "Test: DM @fullpotentialgamebot on Telegram and type /start"
