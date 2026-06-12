#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

state_file="${COMMS_HUB_VAR_DIR:-$(pwd)/var}/state.json"
tick_script="$(pwd)/scripts/comms-hub-cron-tick.sh"

echo "comms_hub_diagnostics=1"
echo "tick_script_exists=$([[ -f "$tick_script" ]] && echo yes || echo no)"
echo "telegram_enabled=${COMMS_HUB_TG_ENABLED:-0}"
echo "telegram_poll_enabled=${COMMS_HUB_TG_POLL_ENABLED:-0}"
echo "telegram_send_enabled=${COMMS_HUB_TG_SEND_ENABLED:-0}"
echo "telegram_token_present=$([[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && echo yes || echo no)"
echo "telegram_allowed_chat_ids_present=$([[ -n "${COMMS_HUB_TG_ALLOWED_CHAT_IDS:-}" ]] && echo yes || echo no)"
echo "state_file_exists=$([[ -f "$state_file" ]] && echo yes || echo no)"

if [[ -f "$state_file" ]]; then
  python3 - "$state_file" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text())
print(f"last_inbox_at={state.get('last_inbox_at', '')}")
print(f"telegram_last_update_id={state.get('telegram_last_update_id', '')}")
PY
else
  echo "last_inbox_at="
  echo "telegram_last_update_id="
fi

echo "suggested_tick=COMMS_HUB_DRY_RUN=1 $tick_script"

