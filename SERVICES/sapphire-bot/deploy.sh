#!/usr/bin/env bash
# Deploy sapphire-bot to primary server.
#
# Secrets must be passed via env vars OR already present in
# /etc/sapphire-bot/sapphire-bot.env on the server.
#
# Usage (first deploy, both keys fresh):
#   SAPPHIRE_BOT_TOKEN="123:ABC..." \
#   ANTHROPIC_API_KEY="sk-ant-..." \
#   bash SERVICES/sapphire-bot/deploy.sh
#
# Usage (just code update):
#   bash SERVICES/sapphire-bot/deploy.sh
#
# Optional: OWNER_TG_ID=12345678 to lock owner before first /start.

set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SERVER="root@198.54.123.234"
REMOTE_DIR="/opt/fpai/services/sapphire-bot"

echo "→ Creating remote dirs + env file..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  mkdir -p $REMOTE_DIR /etc/sapphire-bot /var/lib/sapphire-bot
  if [ -n '${SAPPHIRE_BOT_TOKEN:-}' ] || [ -n '${ANTHROPIC_API_KEY:-}' ] || [ -n '${OWNER_TG_ID:-}' ]; then
    EXISTING='/etc/sapphire-bot/sapphire-bot.env'
    declare -A E
    if [ -f \"\$EXISTING\" ]; then
      while IFS='=' read -r k v; do
        [ -n \"\$k\" ] && [ \"\${k:0:1}\" != '#' ] && E[\$k]=\"\$v\"
      done < \"\$EXISTING\"
    fi
    [ -n '${SAPPHIRE_BOT_TOKEN:-}' ] && E[TELEGRAM_BOT_TOKEN]='${SAPPHIRE_BOT_TOKEN}'
    [ -n '${ANTHROPIC_API_KEY:-}' ]  && E[ANTHROPIC_API_KEY]='${ANTHROPIC_API_KEY}'
    [ -n '${OWNER_TG_ID:-}' ]        && E[OWNER_TG_ID]='${OWNER_TG_ID}'
    [ -z \"\${E[BOT_USERNAME]:-}\" ]    && E[BOT_USERNAME]='LilSapphirebot'
    [ -z \"\${E[ANTHROPIC_MODEL]:-}\" ] && E[ANTHROPIC_MODEL]='claude-sonnet-4-6'
    [ -z \"\${E[LOG_LEVEL]:-}\" ]       && E[LOG_LEVEL]='INFO'
    > \"\$EXISTING\"
    for k in \"\${!E[@]}\"; do echo \"\$k=\${E[\$k]}\" >> \"\$EXISTING\"; done
    chmod 600 \"\$EXISTING\"
    echo '   wrote env file with merged keys'
  else
    if [ ! -f /etc/sapphire-bot/sapphire-bot.env ]; then
      echo '   ⚠️  No vars provided + no existing env file — service will fail to start.'
      echo '   Provide SAPPHIRE_BOT_TOKEN and ANTHROPIC_API_KEY on first deploy.'
    else
      echo '   env file already exists; not overwriting'
    fi
  fi
"

echo "→ Rsyncing service files..."
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  "$ROOT/SERVICES/sapphire-bot/main.py" \
  "$ROOT/SERVICES/sapphire-bot/requirements.txt" \
  "$ROOT/SERVICES/sapphire-bot/sapphire-bot.service" \
  "${SERVER}:${REMOTE_DIR}/"

echo "→ Setup venv + systemd..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  cd $REMOTE_DIR
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
  cp sapphire-bot.service /etc/systemd/system/sapphire-bot.service
  systemctl daemon-reload
  systemctl enable sapphire-bot
  systemctl restart sapphire-bot
  sleep 2
  systemctl is-active sapphire-bot && echo '   service active' || (echo '   service NOT active'; journalctl -u sapphire-bot -n 15 --no-pager)
"

echo ""
echo "✅ sapphire-bot deployed."
echo ""
echo "Next steps:"
echo "  1. Have Cheyenne DM @LilSapphirebot and type /start — first /start claims ownership."
echo "  2. Then /teach her business facts — services, prices, voice, location, ideal client."
echo "  3. Logs: ssh root@198.54.123.234 'journalctl -u sapphire-bot -f'"
