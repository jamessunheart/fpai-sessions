#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_SRC="$REPO_ROOT/core/BUILD/cron/fpai-public-bot.service"
UNIT_DST="/etc/systemd/system/fpai-public-bot.service"

echo "[d126] activating isolated public Sunheart bot"

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "[d126] missing unit artifact: $UNIT_SRC" >&2
  exit 1
fi

if command -v install >/dev/null 2>&1; then
  install -m 0644 "$UNIT_SRC" "$UNIT_DST"
else
  cp "$UNIT_SRC" "$UNIT_DST"
  chmod 0644 "$UNIT_DST"
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload
  if [[ "${PUBLIC_BOT_ACTIVATE:-0}" == "1" ]]; then
    systemctl enable --now fpai-public-bot.service
    systemctl --no-pager --full status fpai-public-bot.service || true
  else
    echo "[d126] unit installed but not started; set PUBLIC_BOT_ACTIVATE=1 when James flips it live"
  fi
else
  echo "[d126] systemctl unavailable; unit copied only"
fi

echo "[d126] rollback: systemctl disable --now fpai-public-bot.service && rm -f $UNIT_DST && systemctl daemon-reload"
