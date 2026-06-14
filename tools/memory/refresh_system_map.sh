#!/usr/bin/env bash
# Thin debounced Cartographer refresh wrapper.
#
# Rebuilds SYSTEM_MAP.md unless a successful refresh happened in the last
# five minutes. The map builder itself owns all map-writing logic.

set -u

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)
STAMP="$HOME/.config/fpai/cartographer_last_refresh"
DEBOUNCE_SECONDS=300

mtime() {
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null
}

if [ -f "$STAMP" ]; then
  LAST=$(mtime "$STAMP" || true)
  NOW=$(date +%s)
  if [ -n "${LAST:-}" ] && [ $((NOW - LAST)) -lt "$DEBOUNCE_SECONDS" ]; then
    echo "skipped (debounce)"
    exit 0
  fi
fi

if [ -z "$SCRIPT_DIR" ] || [ -z "$REPO_ROOT" ]; then
  echo "refresh failed: cannot locate repo root" >&2
  exit 1
fi

python3 "$REPO_ROOT/tools/memory/build_system_map.py"
STATUS=$?
if [ "$STATUS" -eq 0 ]; then
  mkdir -p "$(dirname "$STAMP")"
  touch "$STAMP"
fi
exit "$STATUS"
