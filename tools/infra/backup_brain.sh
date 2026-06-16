#!/usr/bin/env bash
# Daily brain_index backup. Safe to run repeatedly; writes one timestamped dump,
# prunes old local dumps, and best-effort copies offsite when configured.
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/fpai-backup}"
BACKUP_ENV="${BACKUP_ENV:-$HOME/.config/fpai/backup_destinations.env}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"
NOTIFY="${NOTIFY:-/opt/fpai-build/FPAI_Cockpit/tools/build_loop/notify_telegram.sh}"
DB_NAME="${PGDATABASE:-brain_index}"
MIN_BYTES="${BACKUP_MIN_BYTES:-10240}"

log_json() {
  local event="$1"; shift
  python3 - "$OPS_LEDGER" "$event" "$@" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ledger = Path(sys.argv[1])
event = sys.argv[2]
row = {
    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "loop": "brain_backup",
    "event": event,
    "type": event,
    "cost": "$0",
    "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
}
for arg in sys.argv[3:]:
    if "=" not in arg:
        continue
    key, value = arg.split("=", 1)
    if value in ("true", "false"):
        row[key] = value == "true"
        continue
    try:
        if "." in value:
            row[key] = float(value)
        else:
            row[key] = int(value)
        continue
    except ValueError:
        row[key] = value
ledger.parent.mkdir(parents=True, exist_ok=True)
with ledger.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, sort_keys=True) + "\n")
PY
}

notify_failure() {
  local msg="$1"
  if [ -x "$NOTIFY" ]; then
    "$NOTIFY" "🔴 brain_index backup failed: ${msg}" >/dev/null 2>&1 || true
  fi
}

on_error() {
  local line="$1"
  local code="$2"
  local msg="backup_brain.sh failed at line ${line} (exit ${code})"
  log_json backup_failed detail="$msg" offsite=false path="${BACKUP_PATH:-}" next="Ember: inspect fpai-brain-backup.service journal on 162"
  notify_failure "$msg"
  exit "$code"
}
trap 'on_error "$LINENO" "$?"' ERR

if [ "${BACKUP_DISABLE:-0}" = "1" ]; then
  log_json backup_skipped detail="BACKUP_DISABLE=1" offsite=false
  echo "brain backup skipped by BACKUP_DISABLE=1"
  exit 0
fi

if [ -f "$BACKUP_ENV" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$BACKUP_ENV"
  set +a
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" 2>/dev/null || true
repo_real="$(pwd -P)"
backup_real="$(cd "$BACKUP_DIR" && pwd -P)"
case "$backup_real" in
  "$repo_real"|"$repo_real"/*)
    log_json backup_failed detail="refusing repo-local backup directory: $backup_real" offsite=false path="$backup_real"
    notify_failure "refusing repo-local backup directory: $backup_real"
    exit 2
    ;;
esac

stamp="$(date -u +%Y-%m-%d_%H-%M)"
BACKUP_PATH="${BACKUP_DIR}/brain_${stamp}.sql.gz"
tmp="${BACKUP_PATH}.tmp"

if [ -n "${BRAIN_INDEX_DB_URL:-}" ]; then
  pg_dump -Fc "$BRAIN_INDEX_DB_URL" | gzip -c > "$tmp"
elif [ -n "${DATABASE_URL:-}" ]; then
  pg_dump -Fc "$DATABASE_URL" | gzip -c > "$tmp"
elif [ -n "${DB_URL:-}" ]; then
  pg_dump -Fc "$DB_URL" | gzip -c > "$tmp"
else
  PGDATABASE="$DB_NAME" pg_dump -Fc | gzip -c > "$tmp"
fi

gzip -t "$tmp"
size_bytes="$(wc -c < "$tmp" | tr -d ' ')"
if [ "${size_bytes:-0}" -lt "$MIN_BYTES" ]; then
  rm -f "$tmp"
  log_json backup_failed detail="backup too small: ${size_bytes} bytes" size_mb=0 offsite=false path="$BACKUP_PATH" next="Ember: verify pg_dump credentials and brain_index contents"
  notify_failure "backup too small: ${size_bytes} bytes"
  exit 1
fi
mv "$tmp" "$BACKUP_PATH"
chmod 600 "$BACKUP_PATH" 2>/dev/null || true

# Keep the newest 7 local brain dumps.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'brain_*.sql.gz' -printf '%T@ %p\n' 2>/dev/null \
  | sort -rn \
  | awk 'NR>7 {print substr($0, index($0,$2))}' \
  | while IFS= read -r old; do
      [ -n "$old" ] && rm -f -- "$old"
    done

offsite=false
offsite_target=""
if [ -n "${BACKUP_SSH_HOST:-}" ] && [ -n "${BACKUP_SSH_PATH:-}" ]; then
  offsite_target="${BACKUP_SSH_HOST}:${BACKUP_SSH_PATH%/}/$(basename "$BACKUP_PATH")"
  scp -q "$BACKUP_PATH" "$offsite_target"
  offsite=true
elif [ -n "${RCLONE_REMOTE:-}" ]; then
  offsite_target="${RCLONE_REMOTE%/}/$(basename "$BACKUP_PATH")"
  rclone copyto "$BACKUP_PATH" "$offsite_target"
  offsite=true
else
  log_json backup_warning detail="no offsite backup destination configured" offsite=false path="$BACKUP_PATH" next="Set BACKUP_SSH_HOST+BACKUP_SSH_PATH or RCLONE_REMOTE in backup_destinations.env"
fi

size_mb="$(python3 - "$size_bytes" <<'PY'
import sys
print(round(int(sys.argv[1]) / 1024 / 1024, 3))
PY
)"
log_json backup_complete size_mb="$size_mb" size_bytes="$size_bytes" offsite="$offsite" path="$BACKUP_PATH" offsite_target="$offsite_target"
echo "brain backup complete: $BACKUP_PATH (${size_mb} MB, offsite=${offsite})"
