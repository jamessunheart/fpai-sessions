#!/usr/bin/env bash
set -euo pipefail

REPO="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"
SERVICE="fpai-spot-topple.service"
TIMER="fpai-spot-topple.timer"

chmod 0755 "$REPO/core/BUILD/cron/fpai-spot-topple-run.sh"
install -m 0644 "$REPO/core/BUILD/cron/$SERVICE" "$UNIT_DIR/$SERVICE"
install -m 0644 "$REPO/core/BUILD/cron/$TIMER" "$UNIT_DIR/$TIMER"

systemctl daemon-reload
systemctl enable --now "$TIMER"
systemctl list-timers "$TIMER" --no-pager

echo "d194 activation complete: $TIMER installed. Kill switch: touch /opt/fpai-build/.spot_topple_disabled"
