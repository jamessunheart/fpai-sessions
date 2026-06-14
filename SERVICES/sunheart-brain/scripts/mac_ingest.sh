#!/usr/bin/env bash
# One-shot ingest helper on your Mac (uses ingest/.env).
#
#   ./scripts/mac_ingest.sh                 → papers + cursor + 1× Claude (2000 msgs)
#   ./scripts/mac_ingest.sh --claude-only   → only Claude, 15× 2000 msgs
#   ./scripts/mac_ingest.sh --with-bear     → same as default + Bear (needs Full Disk Access)
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ING="$ROOT/ingest"
cd "$ING"

if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -r requirements.txt

CLAUDE_ONLY=false
WITH_BEAR=false
for a in "$@"; do
  case "$a" in
    --claude-only) CLAUDE_ONLY=true ;;
    --with-bear)   WITH_BEAR=true ;;
  esac
done

if ! $CLAUDE_ONLY; then
  echo "== papers ==" && .venv/bin/python brain_ingest.py run --source papers || true
  echo "== cursor ==" && .venv/bin/python brain_ingest.py run --source cursor || true
fi

if $CLAUDE_ONLY; then
  for i in $(seq 1 15); do
    echo "== claude batch $i ==" && .venv/bin/python brain_ingest.py run --source claude --limit 2000 || true
  done
else
  echo "== claude (2000 this run; use --claude-only for 15 batches) =="
  .venv/bin/python brain_ingest.py run --source claude --limit 2000 || true
fi

if $WITH_BEAR; then
  echo "== bear ==" && .venv/bin/python brain_ingest.py run --source bear || true
fi

echo "Done."
