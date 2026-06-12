#!/usr/bin/env bash
# PostToolUse hook for Edit/Write/MultiEdit.
#
# Records that this session has now written to a hot file, so the
# collision-check hook recognizes subsequent edits to the same file as
# self-authored.

set -u

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

REPO_ROOT=$(cd "$(dirname "$FILE_PATH")" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -z "$REPO_ROOT" ] && exit 0

case "$FILE_PATH" in
  "$REPO_ROOT"/*)  REL_PATH="${FILE_PATH#$REPO_ROOT/}" ;;
  *)               exit 0 ;;
esac

# Only log hot files (keeps the log tight).
HOT_LIST="$REPO_ROOT/.claude/hot-files.txt"
[ -f "$HOT_LIST" ] || exit 0

IS_HOT=0
while IFS= read -r pattern; do
  pattern="${pattern#"${pattern%%[![:space:]]*}"}"
  pattern="${pattern%"${pattern##*[![:space:]]}"}"
  [ -z "$pattern" ] && continue
  case "$pattern" in '#'*) continue ;; esac
  if [ "$REL_PATH" = "$pattern" ]; then
    IS_HOT=1
    break
  fi
done < "$HOT_LIST"

[ "$IS_HOT" -eq 0 ] && exit 0

SESSION_DIR="$REPO_ROOT/.claude/sessions/$SESSION_ID"
mkdir -p "$SESSION_DIR" 2>/dev/null
LOG="$SESSION_DIR/edited.txt"

# Append only if not already there (idempotent).
if ! [ -f "$LOG" ] || ! grep -Fxq "$REL_PATH" "$LOG" 2>/dev/null; then
  echo "$REL_PATH" >> "$LOG"
fi

exit 0
