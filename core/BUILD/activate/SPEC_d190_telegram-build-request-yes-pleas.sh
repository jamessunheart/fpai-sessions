#!/usr/bin/env bash
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

src_curator="$REPO/SERVICES/sunheart-brain/curator"
dst_curator="$LIVE/curator"
backup_dir="$LIVE/.d190-backup-$STAMP"
python_bin="$LIVE/.venv/bin/python"

if [ ! -d "$src_curator" ]; then
  echo "d190 activation failed: source curator mirror missing at $src_curator" >&2
  exit 1
fi
if [ ! -d "$dst_curator" ]; then
  echo "d190 activation failed: live curator path missing at $dst_curator" >&2
  exit 1
fi
if [ ! -x "$python_bin" ]; then
  python_bin="/usr/bin/python3"
fi

mkdir -p "$backup_dir"
if [ -f "$dst_curator/tgbot.py" ]; then
  cp -a "$dst_curator/tgbot.py" "$backup_dir/tgbot.py"
fi

install -m 0644 "$src_curator/tgbot.py" "$dst_curator/tgbot.py"
"$python_bin" -m py_compile "$dst_curator/tgbot.py"

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload
  systemctl restart sh-brain-tgbot.service
fi

echo "d190 activation complete: installed Telegram hands-free steering; backup=$backup_dir"
