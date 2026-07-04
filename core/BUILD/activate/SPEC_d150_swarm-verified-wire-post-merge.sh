#!/usr/bin/env bash
# Install the reviewed post-merge reality timer after merge.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

install -m 0644 "$REPO/core/BUILD/cron/fpai-post-merge-reality.service" "$UNIT_DIR/fpai-post-merge-reality.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-post-merge-reality.timer" "$UNIT_DIR/fpai-post-merge-reality.timer"

systemctl daemon-reload
systemctl enable --now fpai-post-merge-reality.timer
systemctl list-timers fpai-post-merge-reality.timer --no-pager

echo "Rollback: systemctl disable --now fpai-post-merge-reality.timer"
