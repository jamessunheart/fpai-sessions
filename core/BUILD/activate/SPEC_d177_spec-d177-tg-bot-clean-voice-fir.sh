#!/usr/bin/env bash
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
LIVE="${SH_BRAIN_SRC:-/opt/sh-brain-src}"
FPAI_ROOT="${FPAI_ROOT:-/opt/fpai}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

src_curator="$REPO/SERVICES/sunheart-brain/curator"
dst_curator="$LIVE/curator"
backup_dir="$LIVE/.d177-backup-$STAMP"

if [ ! -d "$src_curator" ]; then
  echo "d177 activation skipped: source curator mirror missing at $src_curator"
  exit 0
fi
if [ ! -d "$dst_curator" ]; then
  echo "d177 activation skipped: live curator path missing at $dst_curator"
  exit 0
fi

mkdir -p "$backup_dir"
if [ -f "$dst_curator/tgbot.py" ]; then
  cp -a "$dst_curator/tgbot.py" "$backup_dir/tgbot.py"
fi
install -m 0644 "$src_curator/tgbot.py" "$dst_curator/tgbot.py"

python_bin="$LIVE/.venv/bin/python"
if [ ! -x "$python_bin" ]; then
  python_bin="/usr/bin/python3"
fi
"$python_bin" -m py_compile "$dst_curator/tgbot.py"

if [ -f "$FPAI_ROOT/cora-loop/kai_bridge.py" ] && [ -f "$REPO/deploy-tools/kai-bridge.py" ]; then
  cp -a "$FPAI_ROOT/cora-loop/kai_bridge.py" "$backup_dir/kai_bridge.py"
  install -m 0644 "$REPO/deploy-tools/kai-bridge.py" "$FPAI_ROOT/cora-loop/kai_bridge.py"
fi

if [ -f "$FPAI_ROOT/cora-loop/triad_bridge.py" ] && [ -f "$REPO/deploy-tools/triad-bridge.py" ]; then
  cp -a "$FPAI_ROOT/cora-loop/triad_bridge.py" "$backup_dir/triad_bridge.py"
  install -m 0644 "$REPO/deploy-tools/triad-bridge.py" "$FPAI_ROOT/cora-loop/triad_bridge.py"
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl restart sh-brain-tgbot.service
  if [ "${D177_DISABLE_ZV_DIGEST:-1}" = "1" ] && systemctl list-unit-files 'zv-morning-digest.timer' --no-pager --no-legend 2>/dev/null | grep -q '^zv-morning-digest.timer'; then
    systemctl disable --now zv-morning-digest.timer
  fi
fi

echo "d177 activation complete: installed TG bot ACT bridge; quieted CORA bridge copies if present; backup=$backup_dir"
