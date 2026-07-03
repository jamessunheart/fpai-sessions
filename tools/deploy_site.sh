#!/usr/bin/env bash
# Deploy the new FullPotential.com marketplace pages to the live server.
#
# Pushes ONLY the 7 new top-level pages. Does NOT use --delete, so the
# existing /game subdir and everything else on the docroot stay untouched.
# A backup of the old homepage is kept locally as index-game-v1.html.
#
# Usage:  bash tools/deploy_site.sh
# Revert: scp the backup back, or rerun with index-game-v1.html copied over index.html.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/sites/fullpotential-com"
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SERVER="root@198.54.123.234"
REMOTE_PATH="/opt/fpai/core/applications/website-ai/frontend/fullpotential-com"

PAGES=(index.html audit.html ai-builders.html discover.html store.html creators.html experiences.html local.html codex.html)

if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key not found: $SSH_KEY" >&2
  exit 1
fi

# Safety: snapshot the current live homepage before overwriting
echo "→ Backing up live homepage on server → index-prev-$(date +%Y%m%d).html"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" \
  "cp -n $REMOTE_PATH/index.html $REMOTE_PATH/index-prev-$(date +%Y%m%d).html 2>/dev/null || true"

echo "→ Deploying ${#PAGES[@]} pages to ${SERVER}:${REMOTE_PATH}/"
for p in "${PAGES[@]}"; do
  if [ -f "$SRC/$p" ]; then
    rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
      "$SRC/$p" "${SERVER}:${REMOTE_PATH}/$p"
    echo "   ✓ $p"
  else
    echo "   ⚠ skipped (missing): $p"
  fi
done

echo "✅ Done. Live at https://fullpotential.com/ — game preserved at /game"
