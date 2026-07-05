#!/usr/bin/env bash
# Install reviewed d203 chat-based assessment wiring. Run through the live
# service guard after merge; Codex does not run this against production.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
SERVICE_SRC="$REPO/SERVICES/champion-sign/main.py"
SERVICE_LIVE="${CHAMPION_SIGN_LIVE_FILE:-/opt/fpai-build/FPAI_Cockpit/SERVICES/champion-sign/main.py}"
SITE_SRC="$REPO/sites/fullpotential-com/audit.html"
SITE_ROOT="${FULLPOTENTIAL_SITE_ROOT:-/opt/fpai/core/applications/website-ai/frontend/fullpotential-com}"
SERVICE="${CHAMPION_SIGN_SERVICE:-champion-sign.service}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -f "$SERVICE_SRC" ]]; then
  echo "d203 activation failed: missing reviewed champion-sign source at $SERVICE_SRC" >&2
  exit 1
fi
if [[ ! -f "$SITE_SRC" ]]; then
  echo "d203 activation failed: missing reviewed assessment page at $SITE_SRC" >&2
  exit 1
fi

"$PYTHON_BIN" -m py_compile "$SERVICE_SRC"

if [[ "$SERVICE_SRC" != "$SERVICE_LIVE" ]]; then
  install -m 0644 "$SERVICE_SRC" "$SERVICE_LIVE"
  "$PYTHON_BIN" -m py_compile "$SERVICE_LIVE"
  echo "d203 installed champion-sign service file: $SERVICE_LIVE"
else
  echo "d203 champion-sign service file already lives in repo checkout: $SERVICE_LIVE"
fi

if [[ -d "$SITE_ROOT" ]]; then
  install -m 0644 "$SITE_SRC" "$SITE_ROOT/audit.html"
  echo "d203 installed assessment chat page: $SITE_ROOT/audit.html"
else
  echo "d203 site root not present on this host, skipped page install: $SITE_ROOT"
fi

systemctl daemon-reload
systemctl restart "$SERVICE"
sleep 2
systemctl is-active --quiet "$SERVICE"

if command -v curl >/dev/null 2>&1; then
  curl -fsS --max-time 5 http://127.0.0.1:8771/health >/dev/null
  curl -fsS --max-time 5 \
    -H 'Content-Type: application/json' \
    -d '{"state":{},"variant":"activation-smoke"}' \
    http://127.0.0.1:8771/lead/assessment-chat | grep -q '"next_field":"business"'
fi

echo "d203 activation complete: assessment chat endpoint/page installed and $SERVICE healthy"
