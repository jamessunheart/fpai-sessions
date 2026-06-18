#!/usr/bin/env bash
# Append current session insights to brain_index.session_insights.
# Non-blocking: failures are logged by the Python writer and never halt settle.
set -u

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
PYTHON_BIN="${FPAI_PYTHON:-python3}"
INSIGHTS_FILE="${SESSION_INSIGHTS_FILE:-}"
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

args=(
  "${REPO_ROOT}/tools/continuity/write_session_insights.py"
  --session-id "${SESSION_ID}"
  --source "${SESSION_SURFACE:-claude_code}"
)

if [[ -n "${INSIGHTS_FILE}" ]]; then
  args+=(--insights-file "${INSIGHTS_FILE}")
fi

"${PYTHON_BIN}" "${args[@]}" || echo "[session-write-through] write failed (non-blocking)" >&2
exit 0
