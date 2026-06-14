#!/usr/bin/env bash
# Sync Ember's identity stack from the runtime memory dir into the repo mirror.
# Primary location is the runtime path Claude Code reads on session start.
# The repo mirror at core/STATE/identity/ is git-tracked for backup + travel.
#
# Usage: bash tools/sync_identity_to_repo.sh
# Or hook into pre-commit if desired.

set -e

PRIMARY="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MIRROR="$REPO_ROOT/core/STATE/identity"

if [ ! -d "$PRIMARY" ]; then
  echo "❌ Primary identity dir not found: $PRIMARY" >&2
  echo "   This is the runtime source of truth Claude Code reads each session."
  exit 1
fi

mkdir -p "$MIRROR/sessions"

# Copy top-level .md files
for f in "$PRIMARY"/*.md; do
  [ -e "$f" ] && cp "$f" "$MIRROR/"
done

# Copy sessions/
for f in "$PRIMARY"/sessions/*.md; do
  [ -e "$f" ] && cp "$f" "$MIRROR/sessions/"
done

echo "✓ Identity stack synced: $PRIMARY → $MIRROR"
echo ""
echo "Files in mirror:"
ls "$MIRROR" | sed 's/^/  /'
echo ""
echo "  sessions/:"
ls "$MIRROR/sessions" | sed 's/^/    /'
echo ""
echo "Next: review with 'git diff core/STATE/identity/' then commit."
