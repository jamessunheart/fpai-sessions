#!/usr/bin/env bash
# PostToolUse hook for Edit/Write/MultiEdit.
#
# Refreshes the Cartographer map after memory/state/build edits. The refresh is
# backgrounded and debounced, and this hook always exits 0 so editing is never
# blocked by map maintenance.

set -u

main() {
  INPUT=$(cat)
  command -v jq >/dev/null 2>&1 || return 0

  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
  [ -n "$FILE_PATH" ] || return 0

  PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
  if [ -z "$PROJECT_DIR" ]; then
    CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
    if [ -n "$CWD" ]; then
      PROJECT_DIR=$(cd "$CWD" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)
    fi
  fi
  [ -n "$PROJECT_DIR" ] || PROJECT_DIR="$HOME/FPAI_Cockpit"

  case "$FILE_PATH" in
    /*) ABS_PATH="$FILE_PATH" ;;
    *) ABS_PATH="$PROJECT_DIR/$FILE_PATH" ;;
  esac

  TARGET=0
  case "$ABS_PATH" in
    "$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"/*)
      TARGET=1
      ;;
    "$PROJECT_DIR"/memory/*|"$PROJECT_DIR"/core/STATE/*|"$PROJECT_DIR"/core/BUILD/*)
      TARGET=1
      ;;
  esac

  [ "$TARGET" -eq 1 ] || return 0
  [ -x "$PROJECT_DIR/tools/memory/refresh_system_map.sh" ] || return 0

  (
    "$PROJECT_DIR/tools/memory/refresh_system_map.sh" \
      >>"${TMPDIR:-/tmp}/fpai-cartographer-refresh.log" 2>&1
  ) &
}

main || true
exit 0
