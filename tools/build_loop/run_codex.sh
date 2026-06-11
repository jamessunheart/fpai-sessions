#!/usr/bin/env bash
# run_codex.sh — feed pending specs in core/BUILD/specs to Codex (ChatGPT-plan auth),
# capturing each build's output into core/BUILD/results. No copy-paste; no API billing.
#
# Usage:
#   tools/build_loop/run_codex.sh [--target /path/to/repo] [--dry-run]
#
# Auth: uses the logged-in `codex` CLI (~/.codex/auth.json, auth_mode=chatgpt → Max plan).
# A spec is "pending" if specs/<id>.md has no matching results/<id>.result.md.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPECS="$REPO_ROOT/core/BUILD/specs"
RESULTS="$REPO_ROOT/core/BUILD/results"
TARGET="$REPO_ROOT"   # repo Codex builds in; override with --target
DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: codex CLI not on PATH. Install: npm i -g @openai/codex"
  echo "Auth is already present (~/.codex/auth.json, chatgpt mode) — no login needed."
  exit 1
fi

echo "codex: $(command -v codex)  ($(codex --version 2>/dev/null | head -1))"
echo "target repo: $TARGET"

shopt -s nullglob
pending=0
for spec in "$SPECS"/*.md; do
  id="$(basename "$spec" .md)"
  out="$RESULTS/$id.result.md"
  [ -f "$out" ] && continue
  pending=$((pending+1))
  echo "──────────────────────────────────────────"
  echo "BUILD: $id"
  if [ "$DRY" = "1" ]; then
    echo "(dry-run) would run: codex exec --cd '$TARGET' < '$spec'  →  $out"
    continue
  fi
  # Headless build. --full-auto lets Codex edit files + run commands in the target repo.
  # Output (its summary + actions) is tee'd to the result file = the Proof River.
  {
    echo "# Codex build result — $id"
    echo "_ran: $(date -u +%Y-%m-%dT%H:%M:%SZ) · target: $TARGET_"
    echo
    echo '```'
    codex exec --cd "$TARGET" --full-auto - < "$spec" 2>&1 || echo "[codex exited non-zero]"
    echo '```'
  } | tee "$out"
  echo "→ wrote $out"
done

[ "$pending" = "0" ] && echo "No pending specs (all have results)."
echo "done. Review diffs in $TARGET, then write core/BUILD/reviews/<id>.review.md"
