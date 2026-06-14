#!/usr/bin/env bash
# deploy_champion.sh — deploy a Champion's bot to PRIMARY.
#
# Reads core/CHAMPIONS/<slug>.yaml for the Champion's identity, plus secrets
# from env vars (or pre-existing /etc/champion-bot/<slug>.env on the server).
#
# Usage (first deploy):
#   CHAMPION_SLUG=atlas \
#   BOT_TOKEN="123:ABC..." \
#   ANTHROPIC_API_KEY="sk-ant-..." \
#   bash SERVICES/champion-bot/deploy_champion.sh
#
# Usage (code-only update — no env changes):
#   CHAMPION_SLUG=atlas bash SERVICES/champion-bot/deploy_champion.sh
#
# Optional:
#   OWNER_TG_ID=12345    # lock owner before first /start
#   ANTHROPIC_MODEL=claude-sonnet-4-6    # default

set -e

if [ -z "${CHAMPION_SLUG:-}" ]; then
  echo "error: CHAMPION_SLUG must be set (e.g., atlas, halley, josh, sierra, delaney, cheyenne)"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SERVER="root@198.54.123.234"
REMOTE_DIR="/opt/fpai/services/champion-bot"
CFG_FILE="$ROOT/core/CHAMPIONS/${CHAMPION_SLUG}.yaml"
SLUG="$CHAMPION_SLUG"

if [ ! -f "$CFG_FILE" ]; then
  echo "error: config $CFG_FILE not found"
  exit 1
fi

# Extract a few values from the yaml for env-file provisioning + sanity checks.
# Use python3 + yaml since bash can't parse yaml safely.
read_yaml_values() {
  python3 - "$CFG_FILE" <<'PY'
import sys, yaml, shlex
cfg = yaml.safe_load(open(sys.argv[1]).read()) or {}
def emit(k, v):
    if v is None: return
    print(f"YAML_{k}={shlex.quote(str(v))}")
emit("CHAMPION_SLUG", cfg.get("slug", ""))
emit("CHAMPION_NAME", cfg.get("name", ""))
emit("CHAMPION_SHORT_NAME", cfg.get("short_name", ""))
emit("BOT_USERNAME", cfg.get("bot_username", ""))
emit("BOT_PERSONA_NAME", cfg.get("bot_persona_name", ""))
emit("BOT_UNIT_NAME", cfg.get("bot_unit_name", ""))
emit("ROLE_SUMMARY", cfg.get("bot_role_summary", ""))
emit("VOICE_REGISTER", cfg.get("bot_voice_register", ""))
emit("AUDIENCE", cfg.get("bot_audience", ""))
PY
}

eval "$(read_yaml_values)"

if [ -z "${YAML_BOT_USERNAME:-}" ] || [[ "${YAML_BOT_USERNAME}" == *TODO* ]]; then
  echo "error: bot_username in $CFG_FILE is empty or has TODO. Fill it before deploying."
  exit 1
fi
if [ -z "${YAML_ROLE_SUMMARY:-}" ] || [[ "${YAML_ROLE_SUMMARY}" == *TODO* ]]; then
  echo "warning: bot_role_summary contains TODO or is empty — bot will run with degraded prompt."
  read -p "  proceed anyway? [y/N] " ok
  [[ "$ok" =~ ^[Yy]$ ]] || exit 1
fi

ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-sonnet-4-6}"

echo "→ Deploying champion-bot[${SLUG}]"
echo "   bot:    @${YAML_BOT_USERNAME}"
echo "   persona: ${YAML_BOT_PERSONA_NAME}"
echo "   for:    ${YAML_CHAMPION_NAME}"
echo ""

echo "→ Provisioning remote dirs + env file..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  mkdir -p $REMOTE_DIR /etc/champion-bot /var/lib/champion-bot/${SLUG}

  EXISTING='/etc/champion-bot/${SLUG}.env'
  declare -A E
  if [ -f \"\$EXISTING\" ]; then
    while IFS='=' read -r k v; do
      [ -n \"\$k\" ] && [ \"\${k:0:1}\" != '#' ] && E[\$k]=\"\$v\"
    done < \"\$EXISTING\"
  fi

  # Always-from-yaml values (overwrite even if env file exists)
  E[CHAMPION_SLUG]='${YAML_CHAMPION_SLUG}'
  E[CHAMPION_NAME]='${YAML_CHAMPION_NAME}'
  E[CHAMPION_SHORT_NAME]='${YAML_CHAMPION_SHORT_NAME}'
  E[BOT_USERNAME]='${YAML_BOT_USERNAME}'
  E[BOT_PERSONA_NAME]='${YAML_BOT_PERSONA_NAME}'
  E[CHAMPION_ROLE_SUMMARY]='${YAML_ROLE_SUMMARY}'
  E[CHAMPION_VOICE_REGISTER]='${YAML_VOICE_REGISTER}'
  E[CHAMPION_AUDIENCE]='${YAML_AUDIENCE}'
  E[ANTHROPIC_MODEL]='${ANTHROPIC_MODEL}'
  [ -z \"\${E[LOG_LEVEL]:-}\" ] && E[LOG_LEVEL]='INFO'

  # From env (only set if provided this run)
  [ -n '${BOT_TOKEN:-}' ]         && E[TELEGRAM_BOT_TOKEN]='${BOT_TOKEN}'
  [ -n '${ANTHROPIC_API_KEY:-}' ] && E[ANTHROPIC_API_KEY]='${ANTHROPIC_API_KEY}'
  [ -n '${OWNER_TG_ID:-}' ]       && E[OWNER_TG_ID]='${OWNER_TG_ID}'

  if [ -z \"\${E[TELEGRAM_BOT_TOKEN]:-}\" ]; then
    echo '   ⚠️  TELEGRAM_BOT_TOKEN not set — bot will fail to start.'
    echo '   Re-run with: BOT_TOKEN=... CHAMPION_SLUG=${SLUG} bash deploy_champion.sh'
    exit 1
  fi
  if [ -z \"\${E[ANTHROPIC_API_KEY]:-}\" ]; then
    echo '   ⚠️  ANTHROPIC_API_KEY not set — chat features will be disabled.'
  fi

  > \"\$EXISTING\"
  for k in \"\${!E[@]}\"; do printf '%s=%s\n' \"\$k\" \"\${E[\$k]}\" >> \"\$EXISTING\"; done
  chmod 600 \"\$EXISTING\"
  echo '   wrote /etc/champion-bot/${SLUG}.env'
"

echo "→ Rsyncing service code..."
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  "$ROOT/SERVICES/champion-bot/main.py" \
  "$ROOT/SERVICES/champion-bot/requirements.txt" \
  "$ROOT/SERVICES/champion-bot/champion-bot@.service" \
  "${SERVER}:${REMOTE_DIR}/"

echo "→ Setup venv + systemd..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  cd $REMOTE_DIR
  if [ ! -d .venv ]; then python3 -m venv .venv; fi
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt

  # Install templated systemd unit (idempotent)
  cp 'champion-bot@.service' /etc/systemd/system/'champion-bot@.service'
  systemctl daemon-reload
  systemctl enable 'champion-bot@${SLUG}'
  systemctl restart 'champion-bot@${SLUG}'
  sleep 2
  if systemctl is-active --quiet 'champion-bot@${SLUG}'; then
    echo '   service active'
  else
    echo '   service NOT active — recent logs:'
    journalctl -u 'champion-bot@${SLUG}' -n 15 --no-pager
    exit 1
  fi
"

echo ""
echo "✅ champion-bot[${SLUG}] deployed."
echo ""
echo "Next:"
echo "  1. ${YAML_CHAMPION_NAME} DMs @${YAML_BOT_USERNAME} and types /start"
echo "  2. First /start with no owner set auto-claims ownership."
echo "  3. They run /teach for each durable business fact."
echo ""
echo "Logs: ssh root@198.54.123.234 'journalctl -u champion-bot@${SLUG} -f'"
