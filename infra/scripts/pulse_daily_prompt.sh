#!/bin/bash
# pulse_daily_prompt.sh — PULSE daily check-in prompt sender
#
# Fires nightly at 21:00 America/Costa_Rica via LaunchAgent
# (com.sunheart.pulse-daily). Sends James a Telegram message asking him
# to rate yesterday's PULSE 1-5. His response either lands via /pulse
# bot handler (future) or gets manually appended to the ledger.
#
# Reversibility: launchctl unload ~/Library/LaunchAgents/com.sunheart.pulse-daily.plist
# Cost: ~free (Telegram API + 1 short SSH session per day).
#
# Exit codes: 0 ok · 1 ssh/env fetch failed · 2 tg send failed · 3 ledger write failed (non-fatal)
# State: ~/.config/fpai/pulse_daily/{YYYY-MM-DD}.log + last_prompt.json

set -uo pipefail

OUTDIR="${HOME}/.config/fpai/pulse_daily"
LEDGER="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/reference_soul_time_ledger.md"
TODAY="$(date +%Y-%m-%d)"
YESTERDAY="$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d 'yesterday' +%Y-%m-%d)"
TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOG="${OUTDIR}/${TODAY}.log"
LAST_PROMPT="${OUTDIR}/last_prompt.json"

SSH_KEY="${HOME}/.ssh/fpai_deploy_ed25519"
REMOTE_HOST="root@198.54.123.234"
REMOTE_ENV="/etc/fp-game-bot/fp-game-bot.env"

mkdir -p "$OUTDIR"

log() { echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG" >&2; }

# ----- 1. Fetch TG creds from remote --------------------------------------
log "PULSE daily prompt starting · target date=$YESTERDAY"

REMOTE_CREDS="$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "$REMOTE_HOST" "grep -E '^(TELEGRAM_BOT_TOKEN|OWNER_TG_ID)=' $REMOTE_ENV" 2>>"$LOG")" || {
  log "ERROR: SSH fetch of TG creds failed"
  exit 1
}

TG_TOKEN="$(echo "$REMOTE_CREDS" | grep '^TELEGRAM_BOT_TOKEN=' | cut -d= -f2-)"
TG_CHAT="$(echo "$REMOTE_CREDS" | grep '^OWNER_TG_ID=' | cut -d= -f2-)"

if [ -z "$TG_TOKEN" ] || [ -z "$TG_CHAT" ]; then
  log "ERROR: missing TELEGRAM_BOT_TOKEN or OWNER_TG_ID in remote env"
  exit 1
fi

log "credentials fetched (token len=${#TG_TOKEN}, chat=$TG_CHAT)"

# ----- 2. Compose message -------------------------------------------------
# Markdown-safe text. Note: bot is @fullpotentialgamebot (fp-game-bot service).
MSG="🌀 *PULSE check* · rate yesterday (${YESTERDAY}) 1-5
1 = drained · 5 = compounded

Reply with \`/pulse 1-5\` or just the number."

# ----- 3. Send via Telegram API ------------------------------------------
RESP="$(curl -sf -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    --max-time 15 \
    -d "chat_id=${TG_CHAT}" \
    --data-urlencode "text=${MSG}" \
    -d "parse_mode=Markdown" \
    -d "disable_web_page_preview=true" 2>>"$LOG")" || {
  log "ERROR: Telegram sendMessage failed"
  exit 2
}

MSG_ID="$(echo "$RESP" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("result",{}).get("message_id","")) if d.get("ok") else sys.exit(1)' 2>/dev/null || echo "")"

if [ -z "$MSG_ID" ]; then
  log "ERROR: TG response not OK: $(echo "$RESP" | head -c 200)"
  exit 2
fi

log "prompt sent · message_id=$MSG_ID · target_date=$YESTERDAY"

# ----- 4. Persist state for harvester (future) ---------------------------
python3 -c "
import json, sys
state = {
    'sent_at_utc': '$TS_UTC',
    'target_date': '$YESTERDAY',
    'message_id': $MSG_ID,
    'chat_id': '$TG_CHAT',
    'status': 'awaiting_response',
}
with open('$LAST_PROMPT', 'w') as f:
    json.dump(state, f, indent=2)
" 2>>"$LOG" || log "WARN: state persist failed (non-fatal)"

log "state persisted to $LAST_PROMPT"
log "PULSE daily prompt complete."
exit 0
