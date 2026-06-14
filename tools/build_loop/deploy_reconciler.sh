#!/usr/bin/env bash
# deploy_reconciler.sh — ship the position-protection reconciler to the REAL live trader
# (whaletrack-live, port 8601) and drive it on a 2-minute timer. Reversible at every step.
#
# CORRECTED 2026-06-11: prior version targeted whaletrack-magnet (the signal engine, port 8600)
# and spun up a parallel whaletrack-reconciler.service. The live trader holding the open
# positions + the HL agent key is whaletrack-live, and the host already wires
# whaletrack-position-protection.service (WorkingDir=/opt/fpai/services/whaletrack-live).
# This script now ships into whaletrack-live and drives that existing service.
#
# RUN THIS YOURSELF (real-money deploy stays in James's hands — Reserved-Class):
#   bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh           # full deploy (places live stops)
#   bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh --dry     # inventory only, no orders
#
# Reverse everything:  bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh --revert

set -euo pipefail
HOST="root@198.54.123.234"
SSH="ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIVE_DIR="/opt/fpai/services/whaletrack-live"
REMOTE_RECON="$LIVE_DIR/position_protection_reconciler.py"
SVC="whaletrack-position-protection.service"
TIMER="whaletrack-position-protection.timer"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
MODE="${1:-deploy}"

if [ "$MODE" = "--revert" ]; then
  echo "↩︎  Reverting: stop+remove timer, restore last reconciler backup..."
  $SSH "$HOST" '
    systemctl stop '"$TIMER"' 2>/dev/null || true
    systemctl disable '"$TIMER"' 2>/dev/null || true
    rm -f /etc/systemd/system/'"$TIMER"'
    systemctl daemon-reload
    LAST=$(ls -t '"$REMOTE_RECON"'.bak.* 2>/dev/null | head -1)
    [ -n "$LAST" ] && cp "$LAST" '"$REMOTE_RECON"' && echo "restored $LAST"
    echo "timer removed. (reconciler file left in place — harmless)"
  '
  exit 0
fi

DRY=""
[ "$MODE" = "--dry" ] && DRY="--dry-run"

echo "═══ 1/4 · back up + copy fixed reconciler to whaletrack-live ═══"
$SSH "$HOST" "[ -f $REMOTE_RECON ] && cp $REMOTE_RECON $REMOTE_RECON.bak.$STAMP && echo '  backed up to $REMOTE_RECON.bak.$STAMP' || echo '  no prior file to back up'"
$SSH "$HOST" "cat > $REMOTE_RECON" < "$REPO/core/position_protection_reconciler.py"
$SSH "$HOST" "python3 -c 'import ast; ast.parse(open(\"$REMOTE_RECON\").read()); print(\"  syntax OK\")'"

echo "═══ 2/4 · run the reconciler once $DRY (via the existing service env) ═══"
if [ -n "$DRY" ]; then
  # dry-run by hand so we don't change the unit; load the same env files the unit uses
  $SSH "$HOST" '
    set -a; [ -f /etc/fpai/ai.env ] && . /etc/fpai/ai.env
    [ -f '"$LIVE_DIR"'/.env ] && . '"$LIVE_DIR"'/.env; set +a
    cd '"$LIVE_DIR"' && python3 position_protection_reconciler.py --once --dry-run --json 2>&1 | tail -20
  '
  echo "── dry-run done, no orders placed, no timer armed ──"
  exit 0
fi
$SSH "$HOST" "systemctl start $SVC; sleep 3; journalctl -u $SVC --no-pager -n 12 | tail -12"

echo "═══ 3/4 · arm the 2-minute protection timer (drives the existing service) ═══"
$SSH "$HOST" '
cat > /etc/systemd/system/'"$TIMER"' <<UNIT
[Unit]
Description=Run whaletrack position-protection reconciler every 2 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now '"$TIMER"'
systemctl list-timers --no-pager | grep -i protection || true
'

echo "═══ 4/4 · verify resting stops landed ═══"
$SSH "$HOST" '
python3 - <<PY
import json, urllib.request
addr="0xefbfead1189f32bc1000d3740445d0227286b77b"
def info(t):
    r=urllib.request.Request("https://api.hyperliquid.xyz/info",
        data=json.dumps({"type":t,"user":addr}).encode(),headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(r,timeout=10))
oo=[o for o in info("frontendOpenOrders") if o.get("isTrigger")]
print(f"  resting trigger orders now: {len(oo)}")
for o in oo: print("   ", o.get("coin"), "trig=",o.get("triggerPx"), "reduceOnly=",o.get("reduceOnly"))
PY
'
echo "✅ deploy complete. Reverse anytime: bash $0 --revert"
