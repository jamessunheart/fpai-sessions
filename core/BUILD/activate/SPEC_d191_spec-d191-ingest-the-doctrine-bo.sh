#!/usr/bin/env bash
# Install reviewed d191 doctrine ingest + CORE_DOCTRINE bot-context wiring.
# The server build loop runs this through the d182 live_service_guard for
# service backup, smoke, rollback, and alerting.
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE_BRAIN="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
LIVE_INDEX="${SH_BRAIN_INDEX_SRC:-/opt/sh-brain/index}"
CURATOR_ENV="${CURATOR_ENV_FILE:-/etc/sh-brain/curator.env}"

src_curator="$REPO/SERVICES/sunheart-brain/curator"
src_index="$REPO/SERVICES/sunheart-brain/index"
dst_curator="$LIVE_BRAIN/curator"
dst_index="$LIVE_INDEX"
curator_py="$LIVE_BRAIN/.venv/bin/python"
index_py="$LIVE_INDEX/.venv/bin/python"

if [ ! -d "$src_curator" ] || [ ! -d "$dst_curator" ]; then
  echo "d191 activation failed: curator source/live path missing" >&2
  exit 1
fi
if [ ! -d "$src_index" ] || [ ! -d "$dst_index" ]; then
  echo "d191 activation failed: index source/live path missing" >&2
  exit 1
fi
if [ ! -x "$curator_py" ]; then
  curator_py="/usr/bin/python3"
fi
if [ ! -x "$index_py" ]; then
  index_py="/usr/bin/python3"
fi

install -m 0644 "$src_curator/build_context.py" "$dst_curator/build_context.py"
install -m 0644 "$src_curator/tgbot.py" "$dst_curator/tgbot.py"
install -m 0644 "$src_index/ingest_routes.py" "$dst_index/ingest_routes.py"

"$curator_py" -m py_compile "$dst_curator/build_context.py" "$dst_curator/tgbot.py"
"$index_py" -m py_compile "$dst_index/ingest_routes.py"

install -m 0755 "$REPO/core/BUILD/cron/fpai-doctrine-ingest-run.sh" /usr/local/bin/fpai-doctrine-ingest-run.sh
install -m 0644 "$REPO/core/BUILD/cron/fpai-doctrine-ingest.service" /etc/systemd/system/fpai-doctrine-ingest.service
install -m 0644 "$REPO/core/BUILD/cron/fpai-doctrine-ingest.timer" /etc/systemd/system/fpai-doctrine-ingest.timer

if [ -f "$CURATOR_ENV" ]; then
  if grep -q '^SH_CORE_DOCTRINE_MAX_CHARS=' "$CURATOR_ENV"; then
    sed -i 's/^SH_CORE_DOCTRINE_MAX_CHARS=.*/SH_CORE_DOCTRINE_MAX_CHARS=2400/' "$CURATOR_ENV"
  else
    printf '\nSH_CORE_DOCTRINE_MAX_CHARS=2400\n' >> "$CURATOR_ENV"
  fi
fi

systemctl daemon-reload
systemctl restart sh-brain-index.service
systemctl restart sh-brain-tgbot.service
systemctl enable --now fpai-doctrine-ingest.timer
systemctl start fpai-doctrine-ingest.service

echo "d191 activation complete: doctrine ingest timer installed and CORE_DOCTRINE bot context wired"
