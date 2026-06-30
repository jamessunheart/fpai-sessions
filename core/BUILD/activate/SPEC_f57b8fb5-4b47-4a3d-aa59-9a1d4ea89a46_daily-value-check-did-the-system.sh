#!/usr/bin/env bash
# Install the reviewed daily value check timer after merge.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

install -m 0644 "$REPO/core/BUILD/cron/fpai-daily-value-check.service" "$UNIT_DIR/fpai-daily-value-check.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-daily-value-check.timer" "$UNIT_DIR/fpai-daily-value-check.timer"

systemctl daemon-reload
systemctl enable --now fpai-daily-value-check.timer
systemctl list-timers fpai-daily-value-check.timer --no-pager

echo "Rollback: touch /opt/fpai-build/.daily_value_check_disabled"
