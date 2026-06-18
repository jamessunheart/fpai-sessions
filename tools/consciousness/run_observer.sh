#!/usr/bin/env bash
# Non-blocking private consciousness-observer wrapper for settle hooks.
set -euo pipefail

SESSION_PATH="${1:-}"
SESSION_ID="${2:-unknown}"
REPO_ROOT="${FPAI_CODEX_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

if [[ -z "$SESSION_PATH" ]]; then
  exit 0
fi

python3 "$REPO_ROOT/tools/consciousness/loop.py" run-observer \
  --session-path "$SESSION_PATH" \
  --session-id "$SESSION_ID"

