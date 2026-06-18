#!/usr/bin/env bash
set -euo pipefail

SERVICE_ROOT="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
REQ_FILE="$REPO_ROOT/SERVICES/sunheart-brain/curator/requirements.txt"
PY_BIN="$SERVICE_ROOT/.venv/bin/python"
PIP_BIN="$SERVICE_ROOT/.venv/bin/pip"

echo "[d097] activating local Telegram voice pipeline"

if [[ ! -x "$PY_BIN" || ! -x "$PIP_BIN" ]]; then
  echo "[d097] missing bot venv at $SERVICE_ROOT/.venv; skipping package install" >&2
else
  "$PIP_BIN" install -r "$REQ_FILE"
  "$PY_BIN" - <<'PY'
import importlib.util
missing = [
    name for name in ("pipecat", "faster_whisper", "kokoro", "soundfile", "numpy")
    if importlib.util.find_spec(name) is None
]
if missing:
    raise SystemExit(f"missing voice dependencies after install: {', '.join(missing)}")
print("voice dependencies importable")
PY
fi

if command -v ffmpeg >/dev/null 2>&1; then
  echo "[d097] ffmpeg available"
else
  echo "[d097] WARNING: ffmpeg missing; Kokoro TTS cannot become Telegram OGG voice bubbles" >&2
fi

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files sh-brain-tgbot.service >/dev/null 2>&1; then
  systemctl daemon-reload
  systemctl restart sh-brain-tgbot.service
  echo "[d097] restarted sh-brain-tgbot.service"
else
  echo "[d097] sh-brain-tgbot.service not found; no restart performed"
fi
