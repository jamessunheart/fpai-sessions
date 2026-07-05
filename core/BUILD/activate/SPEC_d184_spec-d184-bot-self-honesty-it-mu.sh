#!/usr/bin/env bash
# Install reviewed d184 bot self-honesty fixes. The server build loop runs this
# through the d182 live_service_guard, which handles backup, smoke, rollback,
# and James alerting.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
ENV_FILE="${CURATOR_ENV_FILE:-/etc/sh-brain/curator.env}"
SERVICE_FILE="/etc/systemd/system/sh-brain-tgbot.service"
src_curator="$REPO/SERVICES/sunheart-brain/curator"
dst_curator="$LIVE/curator"
python_bin="$LIVE/.venv/bin/python"

if [ ! -d "$src_curator" ]; then
  echo "d184 activation failed: source curator mirror missing at $src_curator" >&2
  exit 1
fi
if [ ! -d "$dst_curator" ]; then
  echo "d184 activation failed: live curator path missing at $dst_curator" >&2
  exit 1
fi
if [ ! -x "$python_bin" ]; then
  python_bin="/usr/bin/python3"
fi

for file in llm.py tgbot.py voice_pipeline.py build_context.py; do
  install -m 0644 "$src_curator/$file" "$dst_curator/$file"
done

if [ -f "$src_curator/systemd/sh-brain-tgbot.service" ] && [ -w "$(dirname "$SERVICE_FILE")" ]; then
  install -m 0644 "$src_curator/systemd/sh-brain-tgbot.service" "$SERVICE_FILE"
fi

"$python_bin" -m py_compile \
  "$dst_curator/llm.py" \
  "$dst_curator/tgbot.py" \
  "$dst_curator/voice_pipeline.py" \
  "$dst_curator/build_context.py"

if [ -f "$ENV_FILE" ]; then
  if grep -q '^CURATOR_LLM_PROVIDER=' "$ENV_FILE"; then
    sed -i 's/^CURATOR_LLM_PROVIDER=.*/CURATOR_LLM_PROVIDER=claude-cli/' "$ENV_FILE"
  else
    printf '\nCURATOR_LLM_PROVIDER=claude-cli\n' >> "$ENV_FILE"
  fi
  if grep -q '^SH_HOT_STATE_MAX_CHARS=' "$ENV_FILE"; then
    sed -i 's/^SH_HOT_STATE_MAX_CHARS=.*/SH_HOT_STATE_MAX_CHARS=3500/' "$ENV_FILE"
  else
    printf 'SH_HOT_STATE_MAX_CHARS=3500\n' >> "$ENV_FILE"
  fi
  if grep -q '^ANTHROPIC_API_KEY=' "$ENV_FILE"; then
    sed -i 's/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=/' "$ENV_FILE"
  fi
fi

systemctl daemon-reload
systemctl restart sh-brain-tgbot.service
echo "d184 activation complete: installed bot self-honesty health checks and baked Claude/HOT_STATE defaults"
