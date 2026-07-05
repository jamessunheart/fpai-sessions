#!/usr/bin/env bash
# Install reviewed d196 lead worker attribution backup. The browser pixel on
# /assessment is intentionally unchanged; this wires Meta CAPI into the
# post-delivery worker so real delivered leads count even when browsers block
# client-side pixels.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
WORKER_SRC="$REPO/tools/growth/process_leads.py"
UNIT_SRC="$REPO/core/BUILD/fpai-leads-deliver.service"
UNIT_DST="${FPAI_LEADS_DELIVER_UNIT:-/etc/systemd/system/fpai-leads-deliver.service}"
SERVICE="${FPAI_LEADS_DELIVER_SERVICE:-fpai-leads-deliver.service}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
META_ENV="${META_ENV_FILE:-/root/.config/fpai/meta.env}"

if [[ ! -f "$WORKER_SRC" ]]; then
  echo "d196 activation failed: missing reviewed lead worker at $WORKER_SRC" >&2
  exit 1
fi
if [[ ! -f "$UNIT_SRC" ]]; then
  echo "d196 activation failed: missing reviewed service unit at $UNIT_SRC" >&2
  exit 1
fi

"$PYTHON_BIN" -m py_compile "$WORKER_SRC"
install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload

if [[ -f "$META_ENV" ]]; then
  echo "d196 Meta env present: $META_ENV"
else
  echo "d196 warning: $META_ENV not present; CAPI will log missing Meta access token until it exists" >&2
fi

systemctl reset-failed "$SERVICE" >/dev/null 2>&1 || true
echo "d196 activation complete: $SERVICE installed with Meta CAPI env support"
