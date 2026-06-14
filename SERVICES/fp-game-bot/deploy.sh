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
  if [ -n '${FPGAMEBOT_TOKEN:-}' ] || [ -n '${ANTHROPIC_API_KEY:-}' ] || [ -n '${OWNER_TG_ID:-}' ] || [ -n '${ADMIN_TOKEN:-}' ]; then
    # Merge into existing env file (preserve any keys not being updated)
    EXISTING='/etc/fp-game-bot/fp-game-bot.env'
    declare -A E
    if [ -f \"\$EXISTING\" ]; then
      while IFS='=' read -r k v; do
        [ -n \"\$k\" ] && [ \"\${k:0:1}\" != '#' ] && E[\$k]=\"\$v\"
      done < \"\$EXISTING\"
    fi
    [ -n '${FPGAMEBOT_TOKEN:-}' ]   && E[TELEGRAM_BOT_TOKEN]='${FPGAMEBOT_TOKEN}'
    [ -n '${ANTHROPIC_API_KEY:-}' ] && E[ANTHROPIC_API_KEY]='${ANTHROPIC_API_KEY}'
    [ -n '${OWNER_TG_ID:-}' ]       && E[OWNER_TG_ID]='${OWNER_TG_ID}'
    [ -n '${ADMIN_TOKEN:-}' ]       && E[ADMIN_TOKEN]='${ADMIN_TOKEN}'
    [ -z \"\${E[CHAMPION_API_URL]:-}\" ] && E[CHAMPION_API_URL]='https://fullpotential.com/api/champion'
    [ -z \"\${E[GAME_URL]:-}\" ]         && E[GAME_URL]='https://fullpotential.com/game'
    [ -z \"\${E[LOG_LEVEL]:-}\" ]        && E[LOG_LEVEL]='INFO'
    [ -z \"\${E[ANTHROPIC_MODEL]:-}\" ]  && E[ANTHROPIC_MODEL]='claude-haiku-4-5-20251001'
    > \"\$EXISTING\"
    for k in \"\${!E[@]}\"; do echo \"\$k=\${E[\$k]}\" >> \"\$EXISTING\"; done
    chmod 600 \"\$EXISTING\"
    echo '   wrote env file with merged keys'
  else
    if [ ! -f /etc/fp-game-bot/fp-game-bot.env ]; then
      echo '   ⚠️  No vars provided + no existing env file. Service will fail to start.'
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
