#!/usr/bin/env bash
# install_curator_paused.sh — same as install_curator.sh but STOPS before
# enabling the timers. Leaves everything installed, venv ready, units on disk,
# but the curator will NOT run on its own until you:
#
#    systemctl enable --now 'brain-curator-*.timer'
#
# Also supports a manual one-shot at any time:
#    systemctl start brain-curator@digest   # (or dedup / summarize / …)
set -euo pipefail

SRC="/opt/sh-brain-src"
ETC="/etc/sh-brain"
VENV="$SRC/.venv"
SYSTEMD_SRC="$SRC/curator/systemd"

echo "→ writing $ETC/curator.env"
install -d -m 750 "$ETC"
if [ ! -f "$ETC/curator.env" ]; then
  DB_PASS=$(grep BRAIN_INDEX_DB_PASS /root/sh-brain-secrets/brain.env | cut -d= -f2 | tr -d '"')
  cat > "$ETC/curator.env" <<EOF
# brain-curator environment (loaded by systemd)
SH_APPFLOWY_BASE=https://brain.sunheart.com
SH_SECRETS=/root/sh-brain-secrets/brain.env
BRAIN_INDEX_DB_URL=postgres://brain_index:${DB_PASS}@127.0.0.1:25432/appflowy
OLLAMA_BASE=http://127.0.0.1:11434

# LLM for reasoning. Prefer Claude; falls back to Ollama if unset.
# ANTHROPIC_API_KEY=sk-ant-...
# CURATOR_ANTHROPIC_MODEL=claude-sonnet-4-20250514
# CURATOR_OLLAMA_MODEL=llama3.1:8b

CURATOR_DEDUP_MAX_PAIRS=25
CURATOR_CLUSTER_LOOKBACK_H=24
CURATOR_CLUSTER_MIN_SIZE=3
CURATOR_SUMMARIZE_MAX=30
CURATOR_TRIAGE_MAX=40
LOG_LEVEL=INFO
EOF
  chmod 640 "$ETC/curator.env"
else
  echo "  (already exists; leaving untouched)"
fi

echo "→ creating venv at $VENV"
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --upgrade pip >/dev/null
"$VENV/bin/pip" install -r "$SRC/curator/requirements.txt" >/dev/null

echo "→ installing systemd units (NOT enabling)"
install -m 644 "$SYSTEMD_SRC/brain-curator@.service" /etc/systemd/system/
for timer in \
  brain-curator-dedup.timer \
  brain-curator-summarize.timer \
  brain-curator-cluster-tag.timer \
  brain-curator-triage.timer \
  brain-curator-digest.timer \
  brain-curator-apply-approved.timer ; do
  install -m 644 "$SYSTEMD_SRC/$timer" /etc/systemd/system/
done
systemctl daemon-reload

echo
echo "=== INSTALLED · PAUSED ==="
echo "Timers are on disk but NOT enabled. Nothing is running."
echo
echo "Smoke-test manually (safe, one-shot, no timers):"
echo "  systemctl start brain-curator@digest && journalctl -u brain-curator@digest -n 50 --no-pager"
echo
echo "Activate the autonomous loop when ready:"
echo "  for t in brain-curator-{dedup,summarize,cluster-tag,triage,digest,apply-approved}.timer; do"
echo "    systemctl enable --now \$t; done"
