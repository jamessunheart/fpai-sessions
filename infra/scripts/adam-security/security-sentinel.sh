#!/bin/bash
# security-sentinel.sh — permission + secret hygiene (Tier 1: self-healing)
#
# Modes:
#   (no args)     Full scan + auto-fix safe cases + alert if anything remains
#   --quick PATH  Called by inotify watcher; fix one path if it matches rules
#
# Exit 0 if clean after fixes; 1 if issues remain (also sends Telegram).
set -euo pipefail

LOG=/opt/fpai/logs/security-sentinel.log
FIXLOG=/opt/fpai/logs/security-sentinel-autofix.log
ALERTS=""
AUTOFIX_COUNT=0

mkdir -p /opt/fpai/logs
touch "$LOG" "$FIXLOG" 2>/dev/null || true
chmod 600 "$FIXLOG" 2>/dev/null || true

log_autofix() {
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >> "$FIXLOG"
  AUTOFIX_COUNT=$((AUTOFIX_COUNT + 1))
}

append_alert() {
  ALERTS="${ALERTS}${ALERTS:+$'\n'}$1"
}

# --- Telegram (token from openclaw.json; chat from cora-loop .env) ---
send_telegram() {
  local msg="$1"
  local token chat
  token=$(python3 -c "
import json
try:
    d = json.load(open('/root/.openclaw/openclaw.json'))
except Exception:
    exit()
def find(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if 'telegram' in k.lower() and isinstance(v, dict):
                t = v.get('botToken') or v.get('token')
                if t:
                    print(t)
                    return
            find(v)
    elif isinstance(o, list):
        for i in o:
            find(i)
find(d)
" 2>/dev/null | head -1)
  chat=""
  if [ -f /opt/fpai/cora-loop/.env ]; then
    chat=$(grep -E '^TELEGRAM_CHAT_ID=' /opt/fpai/cora-loop/.env | head -1 | cut -d= -f2- | tr -d '\r"'"'"' ')
  fi
  [ -z "$chat" ] && chat="8514069423"
  if [ -n "$token" ] && [ -n "$chat" ]; then
    curl -s -m 15 -X POST "https://api.telegram.org/bot${token}/sendMessage" \
      -d "chat_id=${chat}" --data-urlencode "text=${msg}" >/dev/null || true
  fi
}

# Returns 0 if path is under an allowed root (prefix match).
allowed_path() {
  local f="$1"
  case "$f" in
    /opt/fpai/*|/root/.metaclaw/*|/root/.openclaw/*|/etc/zen-village/*|/tmp/openclaw/*|/var/log/zv-telegram.log) return 0 ;;
    *) return 1 ;;
  esac
}

should_lock_secret_file() {
  local f="$1"
  case "$f" in
    *.env) return 0 ;;
    */secrets/*) return 0 ;;
    */zv-brain.env) return 0 ;;
    */openclaw.json) return 0 ;;
    */mcp-tokens.json) return 0 ;;
    */learnings.json) return 0 ;;
    */mcp-http.env) return 0 ;;
    */telegram.env) return 0 ;;
    /root/.metaclaw/config.yaml) return 0 ;;
    /root/.metaclaw/*.yaml) return 0 ;;
    /root/.metaclaw/*.yml) return 0 ;;
    *) return 1 ;;
  esac
}

fix_secret_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  [ -L "$f" ] && return 0
  allowed_path "$f" || return 0
  should_lock_secret_file "$f" || return 0
  local perm
  perm=$(stat -c "%a" "$f" 2>/dev/null || echo "")
  [ "$perm" = "600" ] && return 0
  if chmod 600 "$f" 2>/dev/null; then
    log_autofix "chmod 600 $f (was $perm)"
  else
    append_alert "🔴 could not chmod 600: $f (was $perm)"
  fi
}

fix_log_others() {
  local f="$1"
  [ -f "$f" ] || return 0
  local perm o
  perm=$(stat -c "%a" "$f" 2>/dev/null || echo "000")
  o="${perm: -1}"
  [ "$o" = "0" ] && return 0
  if chmod o-rw "$f" 2>/dev/null; then
    log_autofix "chmod o-rw $f (was $perm)"
  else
    append_alert "🟡 log still others-readable: $f ($perm)"
  fi
}

run_autofix_pass() {
  local f
  # Explicit high-value files
  for f in \
    /root/.openclaw/openclaw.json \
    /root/.metaclaw/config.yaml \
    /opt/fpai/openclaw/workspace/secrets/zv-brain.env \
    /etc/zen-village/telegram.env \
    /etc/zen-village/mcp-tokens.json \
    /etc/zen-village/mcp-http.env \
    /opt/fpai/cora-loop/.env \
    /opt/fpai/learnings.json; do
    [ -f "$f" ] || continue
    fix_secret_file "$f"
  done

  # All .env under /opt/fpai (bounded depth)
  while IFS= read -r -d '' f; do
    fix_secret_file "$f"
  done < <(find /opt/fpai -maxdepth 8 \( -path '*/node_modules/*' -o -path '*/.git/*' -o -path '*/venv/*' -o -path '*/.venv/*' \) -prune -o -type f -name '.env' -print0 2>/dev/null || true)

  # Known secret filenames anywhere under watched roots
  while IFS= read -r -d '' f; do
    fix_secret_file "$f"
  done < <(find /opt/fpai /etc/zen-village /root/.openclaw /root/.metaclaw -maxdepth 6 \
    \( -path '*/node_modules/*' -o -path '*/.git/*' -o -path '*/venv/*' \) -prune -o \
    -type f \( -name 'mcp-tokens.json' -o -name 'openclaw.json' -o -name 'learnings.json' \) -print0 2>/dev/null || true)

  # Logs: strip others read/write
  for f in /var/log/zv-telegram.log; do
    [ -f "$f" ] && fix_log_others "$f"
  done
  for f in /tmp/openclaw/openclaw-*.log; do
    [ -f "$f" ] || continue
    fix_log_others "$f"
  done
}

# --- quick mode (inotify) ---
if [ "${1:-}" = "--quick" ] && [ -n "${2:-}" ]; then
  path="$2"
  allowed_path "$path" || exit 0
  case "$path" in
    *.log) fix_log_others "$path" ;;
    *) fix_secret_file "$path" ;;
  esac
  exit 0
fi

# --- full scan ---
run_autofix_pass

# Re-check after autofix
for f in /root/.openclaw/openclaw.json /opt/fpai/openclaw/workspace/secrets/zv-brain.env \
  /etc/zen-village/telegram.env /etc/zen-village/mcp-tokens.json \
  /etc/zen-village/mcp-http.env /opt/fpai/cora-loop/.env /opt/fpai/learnings.json; do
  if [ -f "$f" ]; then
    perm=$(stat -c "%a" "$f")
    if [ "$perm" != "600" ]; then
      append_alert "🔴 $f has perm $perm (expected 600)"
    fi
  fi
done

if [ -f /root/.metaclaw/config.yaml ]; then
  perm=$(stat -c "%a" /root/.metaclaw/config.yaml)
  if [ "$perm" != "600" ]; then
    append_alert "🔴 /root/.metaclaw/config.yaml has perm $perm (expected 600)"
  fi
fi

for f in /var/log/zv-telegram.log /tmp/openclaw/openclaw-*.log; do
  for actual in $f; do
    [ -f "$actual" ] || continue
    perm=$(stat -c "%a" "$actual")
    o="${perm: -1}"
    if [ "$o" != "0" ]; then
      append_alert "🟡 $actual has others-readable perm $perm"
    fi
  done
done

LEAKED=""
LEAKED=$(find /opt/fpai /etc/zen-village /root/.openclaw /root/.metaclaw -type f \( -perm -o=r -o -perm -g=r \) \
  \( -name "*.env" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.log" -o -name "*.py" -o -name "*.sh" \) 2>/dev/null \
  | xargs -r grep -lE "bot[0-9]+:AAF|TELEGRAM_BOT_TOKEN=[A-Za-z0-9_-]{20,}|Bearer [a-f0-9]{40}" 2>/dev/null \
  | grep -vE "venv/lib|node_modules|\.bak-|\.backup|\.pre-|security-sentinel\.sh" | head -20) || true
if [ -n "$LEAKED" ]; then
  append_alert "🔴 Files with tokens readable by group/other — autofix may be incomplete:"$'\n'"$LEAKED"
fi

TODAY=$(date -u +"%Y-%m-%d")
HOUR_AGO=$(date -u -d "1 hour ago" +"%Y-%m-%dT%H" 2>/dev/null || date -u -v-1H +"%Y-%m-%dT%H" 2>/dev/null || echo "")
if [ -n "$HOUR_AGO" ] && [ -f "/tmp/openclaw/openclaw-${TODAY}.log" ]; then
  CONFLICTS=$(awk -v h="$HOUR_AGO" '/409: Conflict/ {if (match($0, /T[0-9]{2}:/)) { ts=substr($0,RSTART-10,13); if (ts >= h) print }}' "/tmp/openclaw/openclaw-${TODAY}.log" 2>/dev/null | wc -l | tr -d '[:space:]')
  if [ "${CONFLICTS:-0}" -gt 5 ]; then
    append_alert "🔴 Telegram 409 Conflicts in last hour: $CONFLICTS (ghost poller regression?)"
  fi
fi

for svc in cups avahi-daemon nfs-server rpcbind; do
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    append_alert "🟡 Unneeded service running: $svc"
  fi
done

TS=$(date -u +"%Y-%m-%dT%H:%M")
if [ -n "$ALERTS" ]; then
  echo "[$TS] SECURITY ALERTS (after $AUTOFIX_COUNT autofixes):$ALERTS" >> "$LOG"
  MSG="🛡️ Security Sentinel (post-autofix)
Autofixes this run: $AUTOFIX_COUNT
Remaining issues:
$ALERTS

Re-run: /opt/fpai/openclaw/workspace/tools/security-sentinel.sh"
  send_telegram "$MSG"
  exit 1
else
  echo "[$TS] clean (autofixes=$AUTOFIX_COUNT)" >> "$LOG"
  exit 0
fi
