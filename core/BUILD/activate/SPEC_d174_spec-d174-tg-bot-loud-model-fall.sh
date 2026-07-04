#!/usr/bin/env bash
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

src_curator="$REPO/SERVICES/sunheart-brain/curator"
dst_curator="$LIVE/curator"

if [ ! -d "$src_curator" ]; then
  echo "d174 activation skipped: source curator mirror missing at $src_curator"
  exit 0
fi
if [ ! -d "$dst_curator" ]; then
  echo "d174 activation skipped: live curator path missing at $dst_curator"
  exit 0
fi

backup_dir="$LIVE/.d174-backup-$STAMP"
mkdir -p "$backup_dir"
for file in tgbot.py llm.py build_context.py; do
  if [ -f "$dst_curator/$file" ]; then
    cp -a "$dst_curator/$file" "$backup_dir/$file"
  fi
  install -m 0644 "$src_curator/$file" "$dst_curator/$file"
done

python_bin="$LIVE/.venv/bin/python"
if [ ! -x "$python_bin" ]; then
  python_bin="/usr/bin/python3"
fi
"$python_bin" -m py_compile "$dst_curator/tgbot.py" "$dst_curator/llm.py" "$dst_curator/build_context.py"

systemctl restart sh-brain-tgbot.service
echo "d174 activation complete: installed TG bot model-fallback hardening; backup=$backup_dir"
