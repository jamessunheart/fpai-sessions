#!/usr/bin/env bash
#
# Sunheart Brain — daily backup. Mirrors zv-backup.sh pattern.
# Install via:
#   ln -s /opt/sh-brain/scripts/backup.sh /usr/local/bin/sh-brain-backup.sh
#   (crontab)  15 3 * * * /usr/local/bin/sh-brain-backup.sh
#
# Retains 14 days. Stored under /root/backups/sunheart-brain/<date>/.

set -euo pipefail

DATE=$(date -u +%F)
ROOT=/root/backups/sunheart-brain/$DATE
mkdir -p "$ROOT"

# Postgres
docker exec -e PGPASSWORD="$(grep '^POSTGRES_PASSWORD=' /root/sh-brain-secrets/brain.env | cut -d= -f2)" \
  sh-brain-postgres \
  pg_dump -U appflowy -Fc appflowy > "$ROOT/appflowy_postgres.dump"

# MinIO volume (raw tar from inside container)
docker run --rm -v sh-brain_minio_data:/src -v "$ROOT":/dst alpine \
  sh -c "cd /src && tar czf /dst/minio_data.tar.gz ."

# Secrets + compose env
tar czf "$ROOT/secrets_and_env.tar.gz" \
  /root/sh-brain-secrets/brain.env \
  /etc/sh-brain/*.env \
  /etc/sh-brain/*-tokens.json \
  /opt/sh-brain/compose/docker-compose.yml \
  2>/dev/null || true

cat > "$ROOT/MANIFEST.txt" <<EOF
Sunheart Brain backup — $DATE
  appflowy_postgres.dump   $(du -h "$ROOT/appflowy_postgres.dump" | cut -f1)
  minio_data.tar.gz        $(du -h "$ROOT/minio_data.tar.gz" | cut -f1)
  secrets_and_env.tar.gz   $(du -h "$ROOT/secrets_and_env.tar.gz" | cut -f1)
EOF

# Retention: keep 14 days
find /root/backups/sunheart-brain -maxdepth 1 -type d -mtime +14 -exec rm -rf {} \; 2>/dev/null || true

echo "✓ backup done: $ROOT"
