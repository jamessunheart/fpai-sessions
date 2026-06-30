#!/usr/bin/env bash
# Install the reviewed Autonomous Daily Value timer after merge.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

install -m 0644 "$REPO/core/BUILD/cron/fpai-autonomous-daily-value.service" "$UNIT_DIR/fpai-autonomous-daily-value.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-autonomous-daily-value.timer" "$UNIT_DIR/fpai-autonomous-daily-value.timer"

systemctl daemon-reload
systemctl enable --now fpai-autonomous-daily-value.timer
systemctl list-timers fpai-autonomous-daily-value.timer --no-pager

echo "Rollback: touch /opt/fpai-build/.autonomous_daily_disabled"
