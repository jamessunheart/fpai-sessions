#!/usr/bin/env bash
# Install the reviewed provider-side burn reconciliation timer.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

chmod 0755 "$REPO/tools/burn/reconcile.py"
install -m 0644 "$REPO/core/BUILD/cron/fpai-burn-reconcile.service" "$UNIT_DIR/fpai-burn-reconcile.service"
install -m 0644 "$REPO/core/BUILD/cron/fpai-burn-reconcile.timer" "$UNIT_DIR/fpai-burn-reconcile.timer"

mkdir -p /root/.config/fpai/burn_audit/reports /root/.config/fpai/allocation

systemctl daemon-reload
systemctl enable --now fpai-burn-reconcile.timer
systemctl list-timers fpai-burn-reconcile.timer --no-pager

echo "Rollback: systemctl disable --now fpai-burn-reconcile.timer"
echo "Soft disable: touch /opt/fpai-build/.burn_reconcile_disabled or set BURN_RECONCILE_DISABLE=1"
echo "Admin key setup: store Anthropic admin key at /root/.config/fpai/burn_audit/anthropic_admin_key or ANTHROPIC_ADMIN_API_KEY_FILE."
