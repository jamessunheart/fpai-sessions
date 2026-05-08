#!/usr/bin/env bash
# Deploy the public Game dashboard to fullpotential.com/game
#
# Builds dist/ via gen_cockpit_map.py --public, then rsyncs to the server.
# Usage: bash tools/deploy_game.sh

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SERVER="root@198.54.123.234"
REMOTE_PATH="/opt/fpai/core/applications/website-ai/frontend/fullpotential-com/game"

if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key not found: $SSH_KEY" >&2
  exit 1
fi

echo "→ Building public dist..."
python3 tools/gen_cockpit_map.py --public

if [ ! -f "$ROOT/dist/index.html" ]; then
  echo "❌ Build failed — dist/index.html missing" >&2
  exit 1
fi

SIZE=$(wc -c < "$ROOT/dist/index.html" | tr -d ' ')
echo "→ dist/index.html built (${SIZE} bytes)"

echo "→ Ensuring remote dir exists..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "mkdir -p $REMOTE_PATH"

echo "→ Rsyncing dist/ to ${SERVER}:${REMOTE_PATH}/"
rsync -az --delete \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  "$ROOT/dist/" "${SERVER}:${REMOTE_PATH}/"

# Sync repo's seed champions/proofs/cards to /var/lib/full-potential/ so the
# webhook lookup endpoints see them. Webhook submissions add to this same dir
# (different filenames). Syncing repo files into it merges seed data with
# submitted data without overwriting submissions.
echo "→ Syncing seed champions/proofs/cards to substrate..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "
  mkdir -p /var/lib/full-potential/champions /var/lib/full-potential/proofs /var/lib/full-potential/cards
"
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  --include='*.md' --exclude='INDEX.md' --exclude='registry.json' --exclude='.gitkeep' \
  "$ROOT/core/INTENT/AGREEMENTS/champions/" "${SERVER}:/var/lib/full-potential/champions/" 2>&1 | tail -5 || true
rsync -az -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  --include='*.md' --exclude='.gitkeep' \
  "$ROOT/core/INTENT/AGREEMENTS/proofs/" "${SERVER}:/var/lib/full-potential/proofs/" 2>&1 | tail -5 || true

echo "→ Verifying on server..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "ls -la $REMOTE_PATH/ && head -5 $REMOTE_PATH/index.html"

echo ""
echo "✅ Deployed."
echo ""
echo "Live at: https://fullpotential.com/game"
echo ""
echo "Run 'curl -sI https://fullpotential.com/game | head -3' to verify."
