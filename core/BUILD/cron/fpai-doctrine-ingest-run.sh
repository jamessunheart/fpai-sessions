#!/usr/bin/env bash
# Refresh core/STATE doctrine into brain_index.note_chunks through local embeddings.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
PY="${SH_BRAIN_INDEX_PY:-/opt/sh-brain/index/.venv/bin/python}"
INDEX_ENV="${BRAIN_INDEX_ENV_FILE:-/etc/sh-brain/index.env}"
CURATOR_ENV="${CURATOR_ENV_FILE:-/etc/sh-brain/curator.env}"

if [ ! -x "$PY" ]; then
  PY="/usr/bin/python3"
fi

set -a
[ -f "$INDEX_ENV" ] && . "$INDEX_ENV"
[ -f "$CURATOR_ENV" ] && . "$CURATOR_ENV"
set +a

export FPAI_REPO_ROOT="$REPO"
export SH_BRAIN_BASE="${SH_BRAIN_BASE:-${BRAIN_INDEX_URL:-http://127.0.0.1:28090}}"
export SH_INGEST_TOKEN="${SH_INGEST_TOKEN:-${BRAIN_INDEX_INGEST_TOKEN:-${SH_INDEX_TOKEN:-}}}"

exec "$PY" "$REPO/tools/doctrine/ingest.py" --repo "$REPO" --brain-base "$SH_BRAIN_BASE"
