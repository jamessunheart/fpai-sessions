#!/usr/bin/env bash
# Install reviewed d182 bot guardrail fixes. The server build loop runs this
# through tools/build_loop/live_service_guard.py, which handles backup, smoke,
# rollback, and James alerting.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
ENV_FILE="${CURATOR_ENV_FILE:-/etc/sh-brain/curator.env}"
src_curator="$REPO/SERVICES/sunheart-brain/curator"
dst_curator="$LIVE/curator"
python_bin="$LIVE/.venv/bin/python"

if [ ! -d "$src_curator" ]; then
  echo "d182 activation failed: source curator mirror missing at $src_curator" >&2
  exit 1
fi
if [ ! -d "$dst_curator" ]; then
  echo "d182 activation failed: live curator path missing at $dst_curator" >&2
  exit 1
fi
if [ ! -x "$python_bin" ]; then
  python_bin="/usr/bin/python3"
fi

for file in llm.py tgbot.py voice_pipeline.py; do
  install -m 0644 "$src_curator/$file" "$dst_curator/$file"
done

"$python_bin" -m py_compile "$dst_curator/llm.py" "$dst_curator/tgbot.py" "$dst_curator/voice_pipeline.py"

if [ -f "$ENV_FILE" ]; then
  if grep -q '^CURATOR_LLM_PROVIDER=' "$ENV_FILE"; then
    sed -i 's/^CURATOR_LLM_PROVIDER=.*/CURATOR_LLM_PROVIDER=claude-cli/' "$ENV_FILE"
  else
    printf '\nCURATOR_LLM_PROVIDER=claude-cli\n' >> "$ENV_FILE"
  fi
fi

systemctl restart sh-brain-tgbot.service
echo "d182 activation complete: installed guarded bot Claude/voice/context fixes"
