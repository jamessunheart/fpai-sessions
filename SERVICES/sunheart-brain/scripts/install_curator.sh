#!/usr/bin/env bash
# Install brain-curator on the Secondary server. Run as root after bootstrap.sh
# + install_systemd.sh have already put /opt/sh-brain-src/ and /etc/sh-brain/
# in place.
#
# Creates /etc/sh-brain/curator.env, makes the Python venv, installs deps,
# installs systemd @-service + timers, and enables them.
set -euo pipefail

SRC="/opt/sh-brain-src"
ETC="/etc/sh-brain"
VENV="$SRC/.venv"
SYSTEMD_SRC="$SRC/curator/systemd"

echo "→ writing $ETC/curator.env"
install -d -m 750 "$ETC"
cat > "$ETC/curator.env" <<EOF
# brain-curator environment (loaded by systemd)
SH_APPFLOWY_BASE=https://brain.sunheart.com
SH_SECRETS=/root/sh-brain-secrets/brain.env
BRAIN_INDEX_DB_URL=postgres://brain_index:$(grep BRAIN_INDEX_DB_PASS /root/sh-brain-secrets/brain.env | cut -d= -f2 | tr -d '"')@127.0.0.1:25432/appflowy
OLLAMA_BASE=http://127.0.0.1:11434

# LLM for reasoning. Prefer Claude; falls back to Ollama if unset.
# ANTHROPIC_API_KEY=sk-ant-...
# CURATOR_ANTHROPIC_MODEL=claude-sonnet-4-20250514
# CURATOR_OLLAMA_MODEL=llama3.1:8b

# Tuning
CURATOR_DEDUP_MAX_PAIRS=25
CURATOR_CLUSTER_LOOKBACK_H=24
CURATOR_CLUSTER_MIN_SIZE=3
CURATOR_SUMMARIZE_MAX=30
CURATOR_TRIAGE_MAX=40
LOG_LEVEL=INFO
EOF
chmod 640 "$ETC/curator.env"

echo "→ creating venv at $VENV"
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --upgrade pip >/dev/null
"$VENV/bin/pip" install -r "$SRC/curator/requirements.txt" >/dev/null

echo "→ installing systemd units"
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

echo "→ enabling timers"
for timer in \
  brain-curator-dedup.timer \
  brain-curator-summarize.timer \
  brain-curator-cluster-tag.timer \
  brain-curator-triage.timer \
  brain-curator-digest.timer \
  brain-curator-apply-approved.timer ; do
  systemctl enable --now "$timer"
done

echo
echo "=== DONE ==="
echo "Status:   systemctl list-timers brain-curator-*"
echo "Run now:  systemctl start brain-curator@digest"
echo "Logs:     journalctl -u 'brain-curator@*' -f"
