#!/usr/bin/env bash
# Install the reviewed Forge frontier scan timers after merge.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

install -m 0644 "$REPO/core/BUILD/cron/fpai-forge-daily.service" "$UNIT_DIR/fpai-forge-daily.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-forge-daily.timer" "$UNIT_DIR/fpai-forge-daily.timer"
install -m 0644 "$REPO/core/BUILD/cron/fpai-forge-weekly.service" "$UNIT_DIR/fpai-forge-weekly.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-forge-weekly.timer" "$UNIT_DIR/fpai-forge-weekly.timer"

systemctl daemon-reload
systemctl enable --now fpai-forge-daily.timer
systemctl enable --now fpai-forge-weekly.timer
systemctl list-timers fpai-forge-daily.timer fpai-forge-weekly.timer --no-pager
