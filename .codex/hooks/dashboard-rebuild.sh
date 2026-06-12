#!/usr/bin/env bash
# PostToolUse hook · auto-rebuild dashboard.json whenever core/STATE/DASHBOARD.md changes.
# Silent on success (exit 0). Logs errors to .claude/sessions/<sid>/dashboard-build.log.

set -u

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

REPO_ROOT=$(cd "$(dirname "$FILE_PATH")" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -z "$REPO_ROOT" ] && exit 0

case "$FILE_PATH" in
  "$REPO_ROOT/core/STATE/DASHBOARD.md") ;;
  *) exit 0 ;;
esac

BUILD_SCRIPT="$REPO_ROOT/infra/scripts/dashboard_build.py"
[ -x "$BUILD_SCRIPT" ] || [ -f "$BUILD_SCRIPT" ] || exit 0

LOG_DIR="$REPO_ROOT/.claude/sessions/$SESSION_ID"
mkdir -p "$LOG_DIR" 2>/dev/null
LOG_FILE="$LOG_DIR/dashboard-build.log"

if ! python3 "$BUILD_SCRIPT" >>"$LOG_FILE" 2>&1; then
  echo "[dashboard-rebuild] build FAILED · see $LOG_FILE" >&2
  exit 0
fi

exit 0
