#!/usr/bin/env bash
# Install reviewed d204 Meta comment -> Messenger assessment wiring. This
# restarts champion-sign only; it does not enable live Meta sends.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
SERVICE_SRC="$REPO/SERVICES/champion-sign/main.py"
SERVICE_LIVE="${CHAMPION_SIGN_LIVE_FILE:-/opt/fpai-build/FPAI_Cockpit/SERVICES/champion-sign/main.py}"
SERVICE="${CHAMPION_SIGN_SERVICE:-champion-sign.service}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VERIFY_TOKEN="${META_WEBHOOK_VERIFY_TOKEN:-}"

if [[ ! -f "$SERVICE_SRC" ]]; then
  echo "d204 activation failed: missing reviewed champion-sign source at $SERVICE_SRC" >&2
  exit 1
fi

"$PYTHON_BIN" -m py_compile "$SERVICE_SRC"

if [[ "$SERVICE_SRC" != "$SERVICE_LIVE" ]]; then
  install -m 0644 "$SERVICE_SRC" "$SERVICE_LIVE"
  "$PYTHON_BIN" -m py_compile "$SERVICE_LIVE"
  echo "d204 installed champion-sign service file: $SERVICE_LIVE"
else
  echo "d204 champion-sign service file already lives in repo checkout: $SERVICE_LIVE"
fi

systemctl daemon-reload
systemctl restart "$SERVICE"
sleep 2
systemctl is-active --quiet "$SERVICE"

if command -v curl >/dev/null 2>&1; then
  curl -fsS --max-time 5 http://127.0.0.1:8771/health >/dev/null
  if [[ -n "$VERIFY_TOKEN" ]]; then
    curl -fsS --max-time 5 \
      "http://127.0.0.1:8771/meta/comment-webhook?hub.mode=subscribe&hub.verify_token=${VERIFY_TOKEN}&hub.challenge=d204-ok" \
      | grep -q "d204-ok"
  else
    echo "d204 skipped verify-token smoke: META_WEBHOOK_VERIFY_TOKEN not set in activation environment"
  fi
  curl -fsS --max-time 5 \
    -H 'Content-Type: application/json' \
    -d '{"object":"page","entry":[{"changes":[{"field":"feed","value":{"item":"comment","verb":"add","comment_id":"d204_smoke_comment","post_id":"d204_smoke_post","message":"yes send me the AI assessment score","from":{"id":"d204_smoke_user","name":"Smoke Lead"}}}]}]}' \
    http://127.0.0.1:8771/meta/comment-webhook | grep -q '"would_send"'
fi

echo "d204 activation complete: Meta webhook adapter installed; live Graph API sends remain disabled unless Meta env approval flags are set"
