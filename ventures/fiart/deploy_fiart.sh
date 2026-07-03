#!/usr/bin/env bash
# Deploy Fi-art static site → fiart.org (198 / zen-host). One command, idempotent.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/site" && pwd)/"
HOST="root@198.54.123.234"
DOCROOT="/var/www/fiart.org"

echo "→ syncing $SRC → $HOST:$DOCROOT"
rsync -az --delete -e "ssh -o BatchMode=yes" "$SRC" "$HOST:$DOCROOT/"
ssh -o BatchMode=yes "$HOST" "chown -R www-data:www-data $DOCROOT \
  && find $DOCROOT -type f -exec chmod 644 {} \; \
  && find $DOCROOT -type d -exec chmod 755 {} \;"

echo "→ verifying"
curl -s -o /dev/null -w "https://fiart.org/ → %{http_code}\n" https://fiart.org/ --max-time 15
echo "✓ deployed"
