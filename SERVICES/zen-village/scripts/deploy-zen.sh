#!/usr/bin/env bash
# deploy-zen.sh — one-command deploy for zen-village.
#
# Usage:
#   ./scripts/deploy-zen.sh                  # full deploy: backup + sync + restart + smoke
#   ./scripts/deploy-zen.sh --no-backup      # skip backup (faster, dev-only)
#   ./scripts/deploy-zen.sh --dry-run        # preview rsync changes
#   ./scripts/deploy-zen.sh --bot-only       # only restart bot.py
#   ./scripts/deploy-zen.sh --frontend-only  # only sync frontend/public + reload nginx (none here)
#
# SSH host alias (override with ZEN_SSH_HOST=...). Falls back through:
#   1. zen-host (ProxyJump via fpai2)
#   2. myserver (direct public IP)
#
# Requires:
#   - SSH key admin@server in ssh-agent (`ssh-add ~/.ssh/admin`)
#   - rsync, ssh on PATH locally
#   - Server: /opt/fpai/scripts/pre-deploy-backup.sh (skipped if absent)

set -euo pipefail

# ─── Config ─────────────────────────────────────────────────────────────────
SERVICE="zen-village"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_DIR="/opt/fpai/apps/zen-village"
PUBLIC_URL="${ZEN_PUBLIC_URL:-https://zenvillagecr.com}"
SSH_HOST="${ZEN_SSH_HOST:-}"

# Files & directories to sync (everything else is ignored)
INCLUDE=(
  "main_lite.py"
  "bot.py"
  "app/"
  "frontend/public/"
  "scripts/"
  "requirements.txt"
)

# ─── Args ───────────────────────────────────────────────────────────────────
DO_BACKUP=1
DRY_RUN=0
BOT_ONLY=0
FRONTEND_ONLY=0
for a in "$@"; do
  case "$a" in
    --no-backup) DO_BACKUP=0 ;;
    --dry-run)   DRY_RUN=1 ;;
    --bot-only)  BOT_ONLY=1 ;;
    --frontend-only) FRONTEND_ONLY=1 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $a"; exit 2 ;;
  esac
done

# ─── Pretty ─────────────────────────────────────────────────────────────────
c() { printf "\033[%sm%s\033[0m" "$1" "$2"; }
log()  { printf "%s %s\n" "$(c '36;1' '▶')" "$*"; }
good() { printf "%s %s\n" "$(c '32;1' '✓')" "$*"; }
warn() { printf "%s %s\n" "$(c '33;1' '!')" "$*"; }
die()  { printf "%s %s\n" "$(c '31;1' '✗')" "$*"; exit 1; }

# ─── Resolve SSH host ───────────────────────────────────────────────────────
pick_host() {
  if [[ -n "$SSH_HOST" ]]; then echo "$SSH_HOST"; return; fi
  for h in zen-host myserver fpai; do
    if ssh -o BatchMode=yes -o ConnectTimeout=6 "$h" "hostname" >/dev/null 2>&1; then
      echo "$h"; return
    fi
  done
  return 1
}

log "Resolving SSH host…"
SSH_HOST="$(pick_host)" || die "No SSH path reachable. Add ZEN_SSH_HOST or fix SSH config."
good "Using SSH host: $SSH_HOST"

# ─── Backup ─────────────────────────────────────────────────────────────────
if [[ "$DO_BACKUP" -eq 1 && "$DRY_RUN" -eq 0 ]]; then
  STAMP="v$(date +%Y%m%d-%H%M%S)"
  log "Pre-deploy backup ($STAMP)…"
  if ssh "$SSH_HOST" "test -x /opt/fpai/scripts/pre-deploy-backup.sh"; then
    ssh "$SSH_HOST" "/opt/fpai/scripts/pre-deploy-backup.sh $SERVICE $STAMP" || warn "backup script returned non-zero (continuing)"
  else
    warn "/opt/fpai/scripts/pre-deploy-backup.sh missing — falling back to inline tar"
    ssh "$SSH_HOST" "mkdir -p /opt/fpai/backups/$SERVICE && tar -C /opt/fpai/apps -czf /opt/fpai/backups/$SERVICE/$STAMP.tar.gz $SERVICE && echo 'Backup: /opt/fpai/backups/$SERVICE/$STAMP.tar.gz'"
  fi
fi

# ─── Sync ───────────────────────────────────────────────────────────────────
# IMPORTANT (2026-05-29): images/ is SERVER-AUTHORITATIVE — dwelling photos are
# uploaded via the booking admin UI, NOT tracked in git. They live only on the server.
# History: an earlier deploy used --delete-excluded with an empty local images/ dir,
# which DELETED all 89MB of photos off the live server (zenvillagecr.com went photo-less).
# Two guardrails now prevent recurrence:
#   1. --delete (NOT --delete-excluded): rsync's --delete protects excluded paths from
#      deletion; --delete-excluded would delete them. Never restore --delete-excluded.
#   2. --exclude='images/': the photos dir is never transferred, so an empty/stale local
#      images/ can never overwrite or wipe the server copy.
# To intentionally manage photos, do it server-side or via a dedicated images sync — not here.
RSYNC_FLAGS=(-avz --human-readable --delete
  --exclude='images/'
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.git'
  --exclude='data/' --exclude='*.db' --exclude='*.db-journal' --exclude='*.db-wal'
  --exclude='node_modules' --exclude='.DS_Store')

if [[ "$DRY_RUN" -eq 1 ]]; then RSYNC_FLAGS+=(--dry-run); fi

if [[ "$BOT_ONLY" -eq 1 ]]; then
  PATHS=("bot.py")
elif [[ "$FRONTEND_ONLY" -eq 1 ]]; then
  PATHS=("frontend/public/")
else
  PATHS=("${INCLUDE[@]}")
fi

cd "$LOCAL_DIR"
for rel in "${PATHS[@]}"; do
  if [[ ! -e "$rel" ]]; then
    warn "skip missing: $rel"; continue
  fi
  log "rsync $rel → $SSH_HOST:$REMOTE_DIR/$rel"
  if [[ "$rel" == */ ]]; then
    rsync "${RSYNC_FLAGS[@]}" "$rel" "$SSH_HOST:$REMOTE_DIR/$rel"
  else
    rsync "${RSYNC_FLAGS[@]}" "$rel" "$SSH_HOST:$REMOTE_DIR/$rel"
  fi
done

if [[ "$DRY_RUN" -eq 1 ]]; then good "Dry run done."; exit 0; fi

# ─── Restart ────────────────────────────────────────────────────────────────
SERVICES_TO_RESTART=()
if [[ "$BOT_ONLY" -eq 1 ]]; then
  SERVICES_TO_RESTART=(zen-village-bot)
elif [[ "$FRONTEND_ONLY" -eq 1 ]]; then
  SERVICES_TO_RESTART=()  # static files, no restart needed
else
  SERVICES_TO_RESTART=(zen-village zen-village-bot)
fi

for svc in "${SERVICES_TO_RESTART[@]}"; do
  log "systemctl restart $svc"
  ssh "$SSH_HOST" "systemctl restart $svc"
done

# ─── Smoke ──────────────────────────────────────────────────────────────────
log "Smoke tests…"
ssh "$SSH_HOST" "for s in ${SERVICES_TO_RESTART[*]:-zen-village}; do printf '%-22s %s\n' \"\$s:\" \"\$(systemctl is-active \$s)\"; done"

if [[ "$BOT_ONLY" -eq 0 ]]; then
  for path in /health /api/wallet/rails /wallet /store /menu; do
    code=$(curl -ks -o /dev/null -w '%{http_code}' "$PUBLIC_URL$path") || code="ERR"
    printf '  %-30s %s\n' "$PUBLIC_URL$path" "$code"
  done
fi

good "Deploy complete. URL: $PUBLIC_URL"
