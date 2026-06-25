#!/usr/bin/env bash
# Append current session insights to brain_index.session_insights.
# Auto-generates a minimal insight set from git + alignment if SESSION_INSIGHTS_FILE unset.
# Non-blocking: failures never halt settle.
set -u

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
# Prefer the brain venv (has psycopg); fall back to system python3
PYTHON_BIN="${FPAI_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for _candidate in /opt/sh-brain-src/.venv/bin/python3 /opt/sh-brain-src/.venv/bin/python python3; do
    if command -v "$_candidate" &>/dev/null && "$_candidate" -c "import psycopg" &>/dev/null 2>&1; then
      PYTHON_BIN="$_candidate"; break
    fi
  done
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
INSIGHTS_FILE="${SESSION_INSIGHTS_FILE:-}"
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Ensure DB URL is available (curator.env has a syntax error mid-file that may cut source short)
if [[ -z "${BRAIN_INDEX_DB_URL:-}" ]]; then
  export BRAIN_INDEX_DB_URL
  BRAIN_INDEX_DB_URL=$(grep "^BRAIN_INDEX_DB_URL=" /etc/sh-brain/curator.env 2>/dev/null | cut -d= -f2-)
fi

# Auto-generate minimal insight if no explicit file was provided
if [[ -z "${INSIGHTS_FILE}" ]]; then
  _TMP=$(mktemp /tmp/session_insights_XXXXXX.json)

  # Recent commits this session (last 5)
  _COMMITS=$(git -C "$REPO_ROOT" log --oneline -5 2>/dev/null | head -5 || echo "")
  # Current top-3 from alignment block
  _ALIGNMENT=""
  _ALIGN_FILE="${REPO_ROOT}/identity/ALIGNMENT.md"
  if [[ -f "$_ALIGN_FILE" ]]; then
    _ALIGNMENT=$(grep -A6 "^TOP 3\|^## TOP" "$_ALIGN_FILE" 2>/dev/null | head -8 || echo "")
  fi
  _BODY="Commits: ${_COMMITS} | Alignment: ${_ALIGNMENT}"
  _BODY="${_BODY:0:1000}"

  # Write a single housekeeping insight so the hook is never a no-op
  "${PYTHON_BIN}" -c "
import json, sys
data = [{
    'insight_type': 'housekeeping',
    'title': 'Auto-snapshot: session end',
    'body': sys.argv[1],
    'weight': 3
}]
print(json.dumps(data))
" "$_BODY" > "$_TMP" 2>/dev/null || true

  INSIGHTS_FILE="$_TMP"
fi

args=(
  "${REPO_ROOT}/tools/continuity/write_session_insights.py"
  --session-id "${SESSION_ID}"
  --source "${SESSION_SURFACE:-claude_code}"
  --insights-file "${INSIGHTS_FILE}"
)

# On laptop (no local DB), relay the write to server 162 via SSH
if [[ -z "${BRAIN_INDEX_DB_URL:-}" ]] || ! "${PYTHON_BIN}" -c "
import os, psycopg
try: psycopg.connect(os.environ.get('BRAIN_INDEX_DB_URL',''), connect_timeout=2).close()
except: raise SystemExit(1)
" 2>/dev/null; then
  # DB unreachable locally — relay insight JSON to 162
  if [[ -f "${INSIGHTS_FILE}" ]]; then
    _PAYLOAD=$(cat "${INSIGHTS_FILE}" 2>/dev/null || echo "[]")
    ssh -o BatchMode=yes -o ConnectTimeout=3 root@162.0.208.88 \
      "CLAUDE_SESSION_ID=$(printf '%q' "${SESSION_ID}") SESSION_SURFACE=$(printf '%q' "${SESSION_SURFACE:-claude_code}") \
       /opt/sh-brain-src/.venv/bin/python3 /opt/fpai-build/FPAI_Cockpit/tools/continuity/write_session_insights.py \
       --session-id '${SESSION_ID}' --source '${SESSION_SURFACE:-claude_code}'" \
      <<< "${_PAYLOAD}" >/dev/null 2>&1 || true
  fi
else
  "${PYTHON_BIN}" "${args[@]}" || { echo "[session-write-through] write failed (non-blocking)" >&2; }
fi

# Cleanup temp file if we created it
[[ "${SESSION_INSIGHTS_FILE:-}" == "" && -f "${_TMP:-}" ]] && rm -f "$_TMP" 2>/dev/null || true

"${PYTHON_BIN}" "${REPO_ROOT}/tools/awareness/reliability_probe.py" \
  --send-alert \
  --source after-write \
  --threshold 0.95 \
  || echo "[session-write-through] awareness reliability probe failed (non-blocking)" >&2

# Sync live identity files to repo mirror (keeps HOT_STATE scanner current)
# Copy only — no auto-commit; identity changes land in regular session commits
bash "${REPO_ROOT}/tools/sync_identity_to_repo.sh" 2>/dev/null || true

exit 0
