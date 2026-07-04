#!/usr/bin/env bash
# Install the reviewed campaign-watch timer and guarded actions endpoint.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

chmod 0755 "$REPO/tools/ads/campaign_watch.py"
install -m 0644 "$REPO/core/BUILD/cron/fpai-campaign-watch.service" "$UNIT_DIR/fpai-campaign-watch.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-campaign-watch.timer" "$UNIT_DIR/fpai-campaign-watch.timer"
install -m 0644 "$REPO/core/BUILD/cron/fpai-campaign-actions.service" "$UNIT_DIR/fpai-campaign-actions.service"

mkdir -p /root/.config/fpai/ads /root/.config/fpai/hot_memory /root/.config/fpai/allocation

systemctl daemon-reload
systemctl enable --now fpai-campaign-watch.timer
systemctl enable --now fpai-campaign-actions.service
systemctl list-timers fpai-campaign-watch.timer --no-pager
systemctl --no-pager --full status fpai-campaign-actions.service || true

echo "Rollback: systemctl disable --now fpai-campaign-watch.timer fpai-campaign-actions.service"
echo "Soft disable: touch /opt/fpai-build/.campaign_watch_disabled and/or /opt/fpai-build/.campaign_actions_disabled"
