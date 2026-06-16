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

WT_BASE="$HOME/.fpai-build-worktrees"

shopt -s nullglob
pending=0
for spec in "$SPECS"/*.md; do
  id="$(basename "$spec" .md)"
  out="$RESULTS/$id.result.md"
  [ -f "$out" ] && continue
  pending=$((pending+1))
  if [ "${BUILD_MAX:-0}" -gt 0 ] && [ "$pending" -gt "${BUILD_MAX}" ]; then
    echo "build cap reached (BUILD_MAX=${BUILD_MAX}) — deferring $id + rest to next run"
    break
  fi
  echo "──────────────────────────────────────────"
  echo "BUILD: $id"
  # Isolation: unless --target overrides, each spec builds in its own worktree on
  # branch build/<id> — never the main checkout, where live sessions hold
  # uncommitted work (the collision the .claude hooks exist to prevent).
  BUILD_DIR="$TARGET"
  if [ "$TARGET" = "$REPO_ROOT" ]; then
    BUILD_DIR="$WT_BASE/$id"
    if [ ! -d "$BUILD_DIR" ]; then
      mkdir -p "$WT_BASE"
      git -C "$REPO_ROOT" worktree add -b "build/$id" "$BUILD_DIR" >/dev/null 2>&1 \
        || git -C "$REPO_ROOT" worktree add "$BUILD_DIR" "build/$id" >/dev/null
    fi
    echo "isolated worktree: $BUILD_DIR (branch build/$id)"
  fi
  if [ "$DRY" = "1" ]; then
    echo "(dry-run) would run: codex exec --cd '$BUILD_DIR' < '$spec'  →  $out"
    continue
  fi
  SPEC_INPUT="$spec"
  SPEC_TMP=""
  if [ "${BLUEPRINTS_DISABLE:-0}" != "1" ]; then
    MODULE="$(python3 "$REPO_ROOT/curator/blueprints/manager.py" detect "$id" "$(sed -n '1,160p' "$spec")" 2>/dev/null || true)"
    if [ -n "$MODULE" ]; then
      BLUEPRINT="$(python3 "$REPO_ROOT/curator/blueprints/manager.py" get "$MODULE" 2>/dev/null || true)"
      if [ -n "$BLUEPRINT" ]; then
        SPEC_TMP="$(mktemp "${TMPDIR:-/tmp}/fpai-blueprint-spec.XXXXXX.md")"
        {
          printf '## Existing module blueprint (build against this standard)\n%s\n\n' "$BLUEPRINT"
          cat "$spec"
        } > "$SPEC_TMP"
        SPEC_INPUT="$SPEC_TMP"
      fi
    fi
  fi
  # Headless build. --full-auto lets Codex edit files + run commands in the target repo.
  # Output (its summary + actions) is tee'd to the result file = the Proof River.
  {
    echo "# Codex build result — $id"
    echo "_ran: $(date -u +%Y-%m-%dT%H:%M:%SZ) · target: ${TARGET}_"
    echo
    echo '```'
    codex exec --cd "$BUILD_DIR" --full-auto - < "$SPEC_INPUT" 2>&1 || echo "[codex exited non-zero]"
    echo '```'
  } | tee "$out"
  [ -n "$SPEC_TMP" ] && rm -f "$SPEC_TMP"
  echo "→ wrote $out"
done

[ "$pending" = "0" ] && echo "No pending specs (all have results)."
echo "done. Review diffs in $TARGET, then write core/BUILD/reviews/<id>.review.md"
