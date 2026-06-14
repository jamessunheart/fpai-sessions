#!/usr/bin/env bash
# notify_telegram — surface a message to James's ONE chat (Telegram).
#
# The INPUTS/Steward-interface corner of the Command Constellation: the system
# reaches OUT to James in his one chat instead of him checking files. Used by the
# build pipeline (orchestrator, watcher) to say "built X, ready to merge" etc.
#
#   tools/build_loop/notify_telegram.sh "your message (HTML allowed)"
#
# Reads TELEGRAM_BOT_TOKEN + OWNER_TG_ID from the bot creds (env format).
# Graceful: if creds are missing it logs and exits 0 (never breaks a caller).
# sendMessage does not conflict with the server bot's getUpdates polling.
set -u
MSG="${1:-}"
[ -z "$MSG" ] && { echo "usage: notify_telegram.sh <message>"; exit 2; }
CREDS="${TG_CREDS:-$HOME/.config/fpai/tg_brain/creds.cache}"
[ -f "$CREDS" ] || { echo "notify: no creds at $CREDS (skipped)"; exit 0; }
set -a; . "$CREDS" 2>/dev/null; set +a
TOKEN="${TELEGRAM_BOT_TOKEN:-}"; CHAT="${OWNER_TG_ID:-}"
if [ -z "$TOKEN" ] || [ -z "$CHAT" ]; then echo "notify: token/chat missing (skipped)"; exit 0; fi
if curl -sS --max-time 15 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -d "chat_id=${CHAT}" -d "parse_mode=HTML" --data-urlencode "text=${MSG}" >/dev/null 2>&1; then
  echo "notify: sent to ${CHAT}"
else
  echo "notify: send failed"; exit 1
fi
