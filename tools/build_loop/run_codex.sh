#!/usr/bin/env bash
# run_codex.sh — feed pending specs in core/BUILD/specs to Codex (ChatGPT-plan auth),
# capturing each build's output into core/BUILD/results. No copy-paste; no API billing.
#
# Usage:
#   tools/build_loop/run_codex.sh [--target /path/to/repo] [--spec /path/to/spec.md] [--dry-run]
#
# Auth: uses the logged-in `codex` CLI (~/.codex/auth.json, auth_mode=chatgpt → Max plan).
# A spec is "pending" if specs/<id>.md has no matching results/<id>.result.md.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPECS="$REPO_ROOT/core/BUILD/specs"
RESULTS="$REPO_ROOT/core/BUILD/results"
TARGET="$REPO_ROOT"   # repo Codex builds in; override with --target
DRY=0
ONE_SPEC=""

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --spec) ONE_SPEC="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

if [ "$DRY" != "1" ]; then
  if ! command -v codex >/dev/null 2>&1; then
    echo "ERROR: codex CLI not on PATH. Install: npm i -g @openai/codex"
    echo "Auth is already present (~/.codex/auth.json, chatgpt mode) — no login needed."
    exit 1
  fi
  echo "codex: $(command -v codex)  ($(codex --version 2>/dev/null | head -1))"
else
  echo "codex: dry-run (not checked)"
fi
echo "target repo: $TARGET"

WT_BASE="$HOME/.fpai-build-worktrees"

shopt -s nullglob
pending=0
if [ -n "$ONE_SPEC" ]; then
  specs=("$ONE_SPEC")
else
  specs=("$SPECS"/*.md)
fi

for spec in "${specs[@]}"; do
  [ -f "$spec" ] || continue
  id="$(python3 - "$spec" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="ignore")
if text.startswith("---\n"):
    front = text.split("---\n", 2)[1]
    for line in front.splitlines():
        if line.startswith("id:"):
            print(line.split(":", 1)[1].strip())
            raise SystemExit
stem = path.stem
m = re.match(r"(intent-\d{8}-[0-9a-f]{6})-", stem)
print(m.group(1) if m else stem)
PY
)"
  out="$RESULTS/$id.result.md"
  [ -f "$out" ] && [ -z "$ONE_SPEC" ] && continue
  pending=$((pending+1))
  echo "──────────────────────────────────────────"
  echo "BUILD: $id"
  # Isolation: unless --target overrides, each spec builds in its own worktree on
  # branch build/<id> — never the main checkout, where live sessions hold
  # uncommitted work (the collision the .claude hooks exist to prevent).
  BUILD_DIR="$TARGET"
  if [ "$TARGET" = "$REPO_ROOT" ]; then
    BUILD_DIR="$WT_BASE/$id"
    if [ "$DRY" = "1" ]; then
      echo "isolated worktree: $BUILD_DIR (branch build/$id)"
    elif [ ! -d "$BUILD_DIR" ]; then
      mkdir -p "$WT_BASE"
      git -C "$REPO_ROOT" worktree add -b "build/$id" "$BUILD_DIR" >/dev/null 2>&1 \
        || git -C "$REPO_ROOT" worktree add "$BUILD_DIR" "build/$id" >/dev/null
      echo "isolated worktree: $BUILD_DIR (branch build/$id)"
    else
      echo "isolated worktree: $BUILD_DIR (branch build/$id)"
    fi
  fi
  if [ "$DRY" = "1" ]; then
    echo "(dry-run) would run: codex exec --cd '$BUILD_DIR' < '$spec'  →  $out"
    continue
  fi
  mkdir -p "$RESULTS"
  # Headless build. --full-auto lets Codex edit files + run commands in the target repo.
  # Output (its summary + actions) is tee'd to the result file = the Proof River.
  {
    echo "# Codex build result — $id"
    echo "_ran: $(date -u +%Y-%m-%dT%H:%M:%SZ) · target: $TARGET_"
    echo
    echo '```'
    codex exec --cd "$BUILD_DIR" --full-auto - < "$spec" 2>&1 || echo "[codex exited non-zero]"
    echo '```'
  } | tee "$out"
  echo "→ wrote $out"
done

[ "$pending" = "0" ] && echo "No pending specs (all have results)."
echo "done. Review diffs in $TARGET, then write core/BUILD/reviews/<id>.review.md"
