#!/usr/bin/env bash
# Weekly verification for brain_index backups. Does not touch the live DB.
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/fpai-backup}"
OPS_LEDGER="${OPS_LEDGER:-/opt/fpai-build/ops_ledger.jsonl}"
NOTIFY="${NOTIFY:-/opt/fpai-build/FPAI_Cockpit/tools/build_loop/notify_telegram.sh}"
MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-26}"
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
    "loop": "brain_backup_verify",
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
        row[key] = float(value) if "." in value else int(value)
        continue
    except ValueError:
        row[key] = value
ledger.parent.mkdir(parents=True, exist_ok=True)
with ledger.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, sort_keys=True) + "\n")
PY
}

alert() {
  local msg="$1"
  if [ -x "$NOTIFY" ]; then
    "$NOTIFY" "🔴 brain_index backup verification failed: ${msg}" >/dev/null 2>&1 || true
  fi
}

latest="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'brain_*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -rn | awk 'NR==1 {print $2}')"
if [ -z "$latest" ]; then
  log_json backup_verified valid=false age_hours=-1 size_mb=0 path="" detail="no backup files found"
  alert "no backup files found in $BACKUP_DIR"
  exit 1
fi

now="$(date +%s)"
mtime="$(stat -c %Y "$latest")"
age_hours="$(python3 - "$now" "$mtime" <<'PY'
import sys
print(round((int(sys.argv[1]) - int(sys.argv[2])) / 3600, 2))
PY
)"
size_bytes="$(wc -c < "$latest" | tr -d ' ')"
size_mb="$(python3 - "$size_bytes" <<'PY'
import sys
print(round(int(sys.argv[1]) / 1024 / 1024, 3))
PY
)"

valid=true
detail="ok"
if ! gzip -t "$latest"; then
  valid=false
  detail="gzip integrity check failed"
elif ! gzip -dc "$latest" | pg_restore --list >/dev/null; then
  valid=false
  detail="pg_restore --list failed"
elif python3 - "$age_hours" "$MAX_AGE_HOURS" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) > float(sys.argv[2]) else 1)
PY
then
  valid=false
  detail="newest backup older than ${MAX_AGE_HOURS}h"
elif [ "${size_bytes:-0}" -lt "$MIN_BYTES" ]; then
  valid=false
  detail="backup smaller than ${MIN_BYTES} bytes"
fi

log_json backup_verified valid="$valid" age_hours="$age_hours" size_mb="$size_mb" size_bytes="$size_bytes" path="$latest" detail="$detail"
if [ "$valid" != "true" ]; then
  alert "$detail"
  echo "backup verification failed: $detail"
  exit 1
fi

echo "backup verified: $latest (${age_hours}h old, ${size_mb} MB)"
