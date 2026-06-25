#!/usr/bin/env bash
# Install the reviewed Horizon Scanner timer after merge.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

install -m 0644 "$REPO/core/BUILD/cron/fpai-horizon-scanner.service" "$UNIT_DIR/fpai-horizon-scanner.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-horizon-scanner.timer" "$UNIT_DIR/fpai-horizon-scanner.timer"

systemctl daemon-reload
systemctl enable --now fpai-horizon-scanner.timer
systemctl list-timers fpai-horizon-scanner.timer --no-pager
