#!/bin/bash
# stream_to_tg.sh — unified brain → TG streaming pipeline (Phase 1)
#
# Operationalizes [[project-brain-to-tg-streaming]] + [[identity-continuity-as-embodiment]].
# Routes substrate events (journal · narrator · forge · canonical · trust-tier ·
# sovereignty · cost-impact · alignment) to the right TG channel respecting
# classification tiers and quiet hours.
#
# USAGE:
#   stream_to_tg.sh --category=<cat> --severity=<low|med|high> \
#                   --classification=<PRIVATE|COUNCIL-RESTRICTED|COUNCIL-OPEN|PUBLIC> \
#                   --body="<message body>" \
#                   [--link=<optional canonical link>] \
#                   [--force]   # bypass quiet hours
#
# CATEGORIES (emoji prefix):
#   journal       📓
#   narrator      🔍
#   meta-narrator 🪞
#   forge         ✓
#   canonical     ★
#   trust-tier    🎮
#   sovereignty   🛡️
#   cost-impact   💰
#   alignment     🎯
#   treasury      💎
#   inbox         📥
#   test          🧪
#
# ROUTING (Phase 1):
#   PRIVATE            → James's personal TG channel (OWNER_TG_ID)
#   COUNCIL-RESTRICTED → STUB (logs to ~/.config/fpai/tg_stream/council_restricted.log)
#   COUNCIL-OPEN       → STUB (logs to ~/.config/fpai/tg_stream/council_open.log)
#   PUBLIC             → STUB (logs to ~/.config/fpai/tg_stream/public.log)
#
# QUIET HOURS:
#   22:00-07:00 America/Costa_Rica · non-urgent batched to ~/.config/fpai/tg_stream/queue.tsv
#   severity=high or --force bypasses quiet hours
#   Batched messages flushed at 07:00 by separate cron (or manually via --flush-queue)
#
# OPT-OUT:
#   Edit ~/.config/fpai/tg_stream/muted_categories.txt (one category per line)
#   Muted categories silently drop (still logged to ~/.config/fpai/tg_stream/stream.log).
#
# Reversibility:
#   chmod -x stream_to_tg.sh  → pipeline dies (all callers fail gracefully)
#   rm -rf ~/.config/fpai/tg_stream → reset state
#
# Cost: ~$0 per call (TG API free; SSH session ~free; 1 curl)
#
# Exit codes:
#   0 ok (sent · batched · muted · or stub-logged)
#   1 invalid args
#   2 SSH cred fetch failed
#   3 TG send failed
#   4 classification refused / unknown

set -uo pipefail

# ===== Config ============================================================
STATE_DIR="${HOME}/.config/fpai/tg_stream"
QUEUE_FILE="${STATE_DIR}/queue.tsv"
LOG_FILE="${STATE_DIR}/stream.log"
MUTED_FILE="${STATE_DIR}/muted_categories.txt"
COUNCIL_RESTRICTED_LOG="${STATE_DIR}/council_restricted.log"
COUNCIL_OPEN_LOG="${STATE_DIR}/council_open.log"
PUBLIC_LOG="${STATE_DIR}/public.log"
CREDS_CACHE="${STATE_DIR}/creds.cache"
CREDS_CACHE_TTL_SEC=3600  # refetch creds hourly

SSH_KEY="${HOME}/.ssh/fpai_deploy_ed25519"
REMOTE_HOST="root@198.54.123.234"
REMOTE_ENV="/etc/fp-game-bot/fp-game-bot.env"

QUIET_START_H=22   # 22:00 CR
QUIET_END_H=7      # 07:00 CR
TZ_NAME="America/Costa_Rica"

mkdir -p "$STATE_DIR"
touch "$LOG_FILE" "$MUTED_FILE" "$COUNCIL_RESTRICTED_LOG" "$COUNCIL_OPEN_LOG" "$PUBLIC_LOG"
[ -f "$QUEUE_FILE" ] || echo -e "queued_at_utc\tcategory\tseverity\tclassification\tbody_b64\tlink" > "$QUEUE_FILE"

ts_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts_utc)] $*" >> "$LOG_FILE"; }

# ===== Arg parsing =======================================================
CATEGORY=""
SEVERITY="med"
CLASSIFICATION="PRIVATE"
BODY=""
LINK=""
FORCE=0
FLUSH_QUEUE=0

for arg in "$@"; do
  case "$arg" in
    --category=*)        CATEGORY="${arg#*=}" ;;
    --severity=*)        SEVERITY="${arg#*=}" ;;
    --classification=*)  CLASSIFICATION="${arg#*=}" ;;
    --body=*)            BODY="${arg#*=}" ;;
    --link=*)            LINK="${arg#*=}" ;;
    --force)             FORCE=1 ;;
    --flush-queue)       FLUSH_QUEUE=1 ;;
    *)                   echo "ERROR: unknown arg: $arg" >&2; exit 1 ;;
  esac
done

# ===== Flush queue mode (separate code path) =============================
flush_queue() {
  log "FLUSH_QUEUE invoked"
  if [ ! -s "$QUEUE_FILE" ]; then
    log "queue empty · nothing to flush"
    return 0
  fi
  # Read all queued rows (skip header), send each, then truncate
  local count=0
  while IFS=$'\t' read -r queued_at cat sev cls body_b64 link; do
    [ "$queued_at" = "queued_at_utc" ] && continue   # header
    [ -z "$queued_at" ] && continue
    local decoded_body
    decoded_body=$(echo "$body_b64" | base64 -d 2>/dev/null || echo "")
    [ -z "$decoded_body" ] && continue
    # Send with --force so we don't re-queue
    "$0" --category="$cat" --severity="$sev" --classification="$cls" --body="$decoded_body" --link="$link" --force >/dev/null 2>&1 && count=$((count + 1))
  done < "$QUEUE_FILE"
  # Truncate queue (keep header)
  echo -e "queued_at_utc\tcategory\tseverity\tclassification\tbody_b64\tlink" > "$QUEUE_FILE"
  log "flushed $count queued message(s)"
  return 0
}

if [ "$FLUSH_QUEUE" = "1" ]; then
  flush_queue
  exit 0
fi

# ===== Validation ========================================================
if [ -z "$CATEGORY" ] || [ -z "$BODY" ]; then
  echo "ERROR: --category and --body required" >&2
  echo "USAGE: $0 --category=<cat> --severity=<low|med|high> --classification=<PRIVATE|COUNCIL-RESTRICTED|COUNCIL-OPEN|PUBLIC> --body=\"...\" [--link=...] [--force]" >&2
  exit 1
fi

case "$CLASSIFICATION" in
  PRIVATE|COUNCIL-RESTRICTED|COUNCIL-OPEN|PUBLIC) ;;
  *)
    echo "ERROR: invalid classification '$CLASSIFICATION'" >&2
    exit 4
    ;;
esac

case "$SEVERITY" in low|med|high) ;; *)
  echo "ERROR: severity must be low|med|high (got '$SEVERITY')" >&2
  exit 1
  ;;
esac

# ===== Mute check ========================================================
if grep -qx "$CATEGORY" "$MUTED_FILE" 2>/dev/null; then
  log "MUTED · category=$CATEGORY · body=$(echo "$BODY" | head -c 80)"
  exit 0
fi

# ===== Category → emoji ==================================================
case "$CATEGORY" in
  journal)        EMOJI="📓" ;;
  narrator)       EMOJI="🔍" ;;
  meta-narrator)  EMOJI="🪞" ;;
  forge)          EMOJI="✓" ;;
  canonical)      EMOJI="★" ;;
  trust-tier)     EMOJI="🎮" ;;
  sovereignty)    EMOJI="🛡️" ;;
  cost-impact)    EMOJI="💰" ;;
  alignment)      EMOJI="🎯" ;;
  treasury)       EMOJI="💎" ;;
  inbox)          EMOJI="📥" ;;
  test)           EMOJI="🧪" ;;
  *)              EMOJI="•" ;;
esac

# ===== Quiet hours check (CR time) =======================================
CR_HOUR=$(TZ="$TZ_NAME" date +%H | sed 's/^0//')
in_quiet_hours=0
if [ "$CR_HOUR" -ge "$QUIET_START_H" ] || [ "$CR_HOUR" -lt "$QUIET_END_H" ]; then
  in_quiet_hours=1
fi

if [ "$in_quiet_hours" = "1" ] && [ "$SEVERITY" != "high" ] && [ "$FORCE" = "0" ]; then
  # Queue for morning flush
  BODY_B64=$(echo -n "$BODY" | base64 | tr -d '\n')
  echo -e "$(ts_utc)\t${CATEGORY}\t${SEVERITY}\t${CLASSIFICATION}\t${BODY_B64}\t${LINK}" >> "$QUEUE_FILE"
  log "QUIET_HOURS · queued · category=$CATEGORY · severity=$SEVERITY"
  exit 0
fi

# ===== Format message ====================================================
CR_TIME=$(TZ="$TZ_NAME" date +"%H:%M CR")

# Truncate over-long body to 1000 chars (TG limit safety; can be raised)
TRUNC_BODY="$BODY"
if [ ${#BODY} -gt 1000 ]; then
  TRUNC_BODY="${BODY:0:1000}…"
fi

# Compose: emoji + category + time + body + optional link
MSG="${EMOJI} ${CR_TIME} · ${TRUNC_BODY}"
[ -n "$LINK" ] && MSG="${MSG}
↳ ${LINK}"

# ===== Route by classification ===========================================
case "$CLASSIFICATION" in
  COUNCIL-RESTRICTED)
    echo -e "$(ts_utc)\t${CATEGORY}\t${SEVERITY}\t${MSG//$'\n'/ }" >> "$COUNCIL_RESTRICTED_LOG"
    log "STUB → council_restricted.log · category=$CATEGORY"
    exit 0
    ;;
  COUNCIL-OPEN)
    echo -e "$(ts_utc)\t${CATEGORY}\t${SEVERITY}\t${MSG//$'\n'/ }" >> "$COUNCIL_OPEN_LOG"
    log "STUB → council_open.log · category=$CATEGORY"
    exit 0
    ;;
  PUBLIC)
    echo -e "$(ts_utc)\t${CATEGORY}\t${SEVERITY}\t${MSG//$'\n'/ }" >> "$PUBLIC_LOG"
    log "STUB → public.log · category=$CATEGORY"
    exit 0
    ;;
  PRIVATE)
    # Falls through to TG send below
    ;;
esac

# ===== PRIVATE path · fetch creds (with cache) ===========================
need_refetch=1
if [ -f "$CREDS_CACHE" ]; then
  cache_age=$(( $(date +%s) - $(stat -f %m "$CREDS_CACHE" 2>/dev/null || stat -c %Y "$CREDS_CACHE" 2>/dev/null || echo 0) ))
  if [ "$cache_age" -lt "$CREDS_CACHE_TTL_SEC" ]; then
    need_refetch=0
  fi
fi

if [ "$need_refetch" = "1" ]; then
  if REMOTE_CREDS=$(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
      "$REMOTE_HOST" "grep -E '^(TELEGRAM_BOT_TOKEN|OWNER_TG_ID)=' $REMOTE_ENV" 2>>"$LOG_FILE"); then
    echo "$REMOTE_CREDS" > "$CREDS_CACHE"
    chmod 600 "$CREDS_CACHE"
  else
    log "ERROR: SSH cred fetch failed"
    exit 2
  fi
fi

TG_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$CREDS_CACHE" | cut -d= -f2-)
TG_CHAT=$(grep '^OWNER_TG_ID=' "$CREDS_CACHE" | cut -d= -f2-)

if [ -z "$TG_TOKEN" ] || [ -z "$TG_CHAT" ]; then
  log "ERROR: missing TG_TOKEN or OWNER_TG_ID in cache"
  exit 2
fi

# ===== Send to TG ========================================================
RESP=$(curl -sf -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
  --max-time 15 \
  -d "chat_id=${TG_CHAT}" \
  --data-urlencode "text=${MSG}" \
  -d "disable_web_page_preview=true" 2>>"$LOG_FILE") || {
  log "ERROR: TG send failed · category=$CATEGORY · resp=$(echo "$RESP" | head -c 200)"
  exit 3
}

MSG_ID=$(echo "$RESP" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("result",{}).get("message_id","")) if d.get("ok") else sys.exit(1)' 2>/dev/null || echo "")

if [ -z "$MSG_ID" ]; then
  log "ERROR: TG response not OK · category=$CATEGORY · resp=$(echo "$RESP" | head -c 200)"
  exit 3
fi

log "SENT · msg_id=$MSG_ID · category=$CATEGORY · severity=$SEVERITY"
exit 0
