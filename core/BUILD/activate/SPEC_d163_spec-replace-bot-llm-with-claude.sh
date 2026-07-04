#!/usr/bin/env bash
# Install the reviewed claude-cli LLM provider and flip the Telegram bot to it.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
SERVICE_ROOT="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
ENV_FILE="${CURATOR_ENV_FILE:-/etc/sh-brain/curator.env}"
SERVICE="${CURATOR_TGBOT_SERVICE:-sh-brain-tgbot.service}"
SRC="$REPO/SERVICES/sunheart-brain/curator/llm.py"
LIVE="$SERVICE_ROOT/curator/llm.py"
PY_BIN="$SERVICE_ROOT/.venv/bin/python"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_DIR="$SERVICE_ROOT/.deploy-backups/d163-claude-cli-$STAMP"

echo "[d163] activating claude-cli curator LLM provider"

if [[ ! -f "$SRC" ]]; then
  echo "[d163] missing reviewed source: $SRC" >&2
  exit 1
fi
if [[ ! -f "$LIVE" ]]; then
  echo "[d163] missing live llm.py: $LIVE" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[d163] missing curator env file: $ENV_FILE" >&2
  exit 1
fi
if [[ ! -x "$PY_BIN" ]]; then
  echo "[d163] missing executable bot python: $PY_BIN" >&2
  exit 1
fi

python3 -m py_compile "$SRC"
mkdir -p "$BACKUP_DIR"
cp -p "$LIVE" "$BACKUP_DIR/llm.py"
cp -p "$ENV_FILE" "$BACKUP_DIR/curator.env"

install -m 0644 "$SRC" "$LIVE"
"$PY_BIN" -m py_compile "$LIVE"

if grep -q '^CURATOR_LLM_PROVIDER=' "$ENV_FILE"; then
  sed -i 's/^CURATOR_LLM_PROVIDER=.*/CURATOR_LLM_PROVIDER=claude-cli/' "$ENV_FILE"
else
  printf '\nCURATOR_LLM_PROVIDER=claude-cli\n' >> "$ENV_FILE"
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload
  systemctl restart "$SERVICE"
  sleep 4
  systemctl is-active --quiet "$SERVICE"
  echo "[d163] restarted $SERVICE and it is active"
else
  echo "[d163] systemctl unavailable; installed files and env only"
fi

echo "[d163] backup: $BACKUP_DIR"
echo "[d163] rollback: cp -p $BACKUP_DIR/llm.py $LIVE && cp -p $BACKUP_DIR/curator.env $ENV_FILE && systemctl restart $SERVICE"
echo "[d163] proof: journalctl -u $SERVICE --since '30 minutes ago' --no-pager | grep -F 'api.anthropic.com' should return no rows"
