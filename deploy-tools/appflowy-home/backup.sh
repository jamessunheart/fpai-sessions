#!/usr/bin/env bash
# Nightly sovereign backup: encrypted dump of AppFlowy postgres + minio objects.
# Cron: 0 3 * * *  bash /srv/appflowy/backup.sh
# Restore test monthly — a backup you haven't restored is a hope, not a backup.
set -euo pipefail

STACK_DIR="${STACK_DIR:-/srv/appflowy/AppFlowy-Cloud}"
OUT="${OUT:-/srv/backups/appflowy}"           # put this on a SECOND drive
GPG_RECIPIENT="${GPG_RECIPIENT:-}"            # your GPG key id, for encryption
STAMP="$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

cd "$STACK_DIR"

echo "== postgres dump =="
docker compose exec -T postgres pg_dumpall -U postgres > "$OUT/pg-$STAMP.sql"

echo "== minio objects =="
# mirror the object store volume (adjust volume/container names if different)
docker run --rm --volumes-from "$(docker compose ps -q minio)" \
  -v "$OUT:/backup" alpine tar czf "/backup/minio-$STAMP.tgz" /data 2>/dev/null || \
  echo "  (adjust minio volume path if this errors)"

echo "== encrypt (if GPG key set) =="
if [ -n "$GPG_RECIPIENT" ]; then
  for f in "$OUT/pg-$STAMP.sql" "$OUT/minio-$STAMP.tgz"; do
    [ -f "$f" ] && gpg --yes --encrypt -r "$GPG_RECIPIENT" "$f" && rm -f "$f"
  done
fi

echo "== prune backups older than 30 days =="
find "$OUT" -type f -mtime +30 -delete

echo "DONE $STAMP → $OUT  (now copy off-site: rsync/rclone to a location YOU control)"
