#!/usr/bin/env bash
# Sync Ember's identity stack from the runtime memory dir into the repo mirror.
# Primary location is the runtime path Claude Code reads on session start.
# The repo mirror at core/STATE/identity/ is git-tracked for backup + travel.
#
# Usage: bash tools/sync_identity_to_repo.sh
# Or hook into pre-commit if desired.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MIRROR="$REPO_ROOT/core/STATE/identity"

# Find the primary identity dir — try repo-local path first, then laptop path
for _candidate in \
    "$HOME/.claude/projects/-opt-fpai-build-FPAI_Cockpit/memory/identity" \
    "$HOME/.claude/projects/-opt-fpai-build-FPAI-Cockpit/memory/identity" \
    "$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"; do
  if [ -d "$_candidate" ]; then
    PRIMARY="$_candidate"
    break
  fi
done

if [ -z "${PRIMARY:-}" ] || [ ! -d "$PRIMARY" ]; then
  echo "❌ Primary identity dir not found (tried laptop + 162 paths)" >&2
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
