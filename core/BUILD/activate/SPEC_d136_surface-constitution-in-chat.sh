#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
STATE_FILE="${D136_CONSTITUTION_SURFACE_STATE:-/var/lib/fpai-build/d136_constitution_sent}"

echo "[d136] surfacing current repo constitution into James's Telegram chat"

if [[ ! -f "$REPO_ROOT/tools/constitution/surface.py" ]]; then
  echo "[d136] missing constitution surfacer: $REPO_ROOT/tools/constitution/surface.py" >&2
  exit 1
fi

python3 "$REPO_ROOT/tools/constitution/surface.py" \
  --repo-root "$REPO_ROOT" \
  --send \
  --state-file "$STATE_FILE"

echo "[d136] rollback: remove $STATE_FILE to allow a future resend, or revert SPEC_d136 files"
