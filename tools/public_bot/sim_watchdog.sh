#!/usr/bin/env bash
set -u
: "${HOME:=/root}"
cd /opt/fpai-build/FPAI_Cockpit || exit 1
set -a; . /root/.config/fpai/claude.env 2>/dev/null; set +a
LOG=/opt/fpai-build/public_bot_sim.log
OUT=$(timeout 600 /opt/sh-brain-src/.venv/bin/python -m tools.public_bot.sim_chat --n 3 --turns 3 2>&1)
echo "===== $(date -u +%Y-%m-%dT%H:%M:%SZ) =====" >> "$LOG"
echo "$OUT" | grep -E "JUDGE:|=====" >> "$LOG"
# alert if any leak true
if echo "$OUT" | grep -qiE '"leaked":[[:space:]]*true'; then
  echo "ALERT: public bot LEAKED in sim — $(date -u)" >> "$LOG"
  TG=$(grep -hoE 'TG[A-Z_]*TOKEN=[^ ]+|BOT_TOKEN=[^ ]+' /etc/sh-brain/curator.env 2>/dev/null | head -1 | cut -d= -f2)
  CID=$(grep -hoE 'TELEGRAM_CHAT_ID=[^ ]+' /etc/sh-brain/curator.env 2>/dev/null | head -1 | cut -d= -f2)
  [ -n "$TG" ] && [ -n "$CID" ] && curl -s "https://api.telegram.org/bot$TG/sendMessage" -d chat_id="$CID" -d text="🔴 Public bot sim LEAKED private info — review before live release." >/dev/null
fi
