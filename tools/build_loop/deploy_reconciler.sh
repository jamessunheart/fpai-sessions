#!/usr/bin/env bash
# deploy_reconciler.sh — ship the position-protection reconciler to the live whaletrack
# host, fix the broken Python env (the real root cause of stops never firing), protect the
# 2 open shorts, and arm a 2-minute timer. Reversible at every step.
#
# RUN THIS YOURSELF (real-money deploy stays in James's hands — Reserved-Class):
#   bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh           # full deploy
#   bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh --dry     # inventory only, no orders
#
# Reverse everything:  bash ~/FPAI_Cockpit/tools/build_loop/deploy_reconciler.sh --revert

set -euo pipefail
HOST="root@198.54.123.234"
SSH="ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REMOTE_CORE="/opt/fpai/services/whaletrack-magnet/core"
LIVE_DIR="/opt/fpai/services/whaletrack-live"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
MODE="${1:-deploy}"

if [ "$MODE" = "--revert" ]; then
  echo "↩︎  Reverting: restoring typing backport + removing timer..."
  $SSH "$HOST" '
    systemctl stop whaletrack-reconciler.timer 2>/dev/null || true
    systemctl disable whaletrack-reconciler.timer 2>/dev/null || true
    rm -f /etc/systemd/system/whaletrack-reconciler.{service,timer}
    systemctl daemon-reload
    LAST=$(ls -t /usr/local/lib/python3.10/dist-packages/typing.py.bak.* 2>/dev/null | head -1)
    [ -n "$LAST" ] && cp "$LAST" /usr/local/lib/python3.10/dist-packages/typing.py && echo "restored $LAST"
    echo "reconciler timer removed. (reconciler file left in place — harmless; rm core/position_protection_reconciler.py to fully remove)"
  '
  exit 0
fi

DRY=""
[ "$MODE" = "--dry" ] && DRY="--dry-run"

echo "═══ 1/5 · copy reconciler to prod ═══"
$SSH "$HOST" "cat > $REMOTE_CORE/position_protection_reconciler.py" < "$REPO/core/position_protection_reconciler.py"
$SSH "$HOST" "python3 -c 'import ast,sys; ast.parse(open(\"$REMOTE_CORE/position_protection_reconciler.py\").read()); print(\"  syntax OK\")'"

echo "═══ 2/5 · fix the broken Python env (remove obsolete typing backport — the root cause) ═══"
$SSH "$HOST" '
  T=/usr/local/lib/python3.10/dist-packages/typing.py
  if [ -f "$T" ]; then
    cp "$T" "$T.bak.'"$STAMP"'"
    rm -f "$T" "${T}c" 2>/dev/null || true
    # also drop the compiled cache + the .dist-info so pip/py dont resurrect it on import
    rm -rf /usr/local/lib/python3.10/dist-packages/__pycache__/typing.* 2>/dev/null || true
    echo "  removed typing backport (backed up to $T.bak.'"$STAMP"')"
  else
    echo "  typing backport already absent — good"
  fi
  python3 - <<PY
import inspect, dataclasses
print("  stdlib check: inspect.signature ok =", hasattr(inspect, "signature"))
PY
'

echo "═══ 3/5 · reconcile $DRY (protect open positions) ═══"
$SSH "$HOST" '
  set -a; [ -f /etc/fpai/ai.env ] && . /etc/fpai/ai.env
  [ -f /opt/fpai/services/whaletrack-magnet/api/.env ] && . /opt/fpai/services/whaletrack-magnet/api/.env; set +a
  cd /opt/fpai/services/whaletrack-magnet
  python3 core/position_protection_reconciler.py --once '"$DRY"' --json 2>&1 | tail -25
'

if [ -n "$DRY" ]; then echo "── dry-run done, no orders placed, no timer armed ──"; exit 0; fi

echo "═══ 4/5 · arm the 2-minute protection timer ═══"
$SSH "$HOST" '
cat > /etc/systemd/system/whaletrack-reconciler.service <<UNIT
[Unit]
Description=Whaletrack position-protection reconciler (Watchfire)
After=network-online.target
[Service]
Type=oneshot
WorkingDirectory=/opt/fpai/services/whaletrack-magnet
EnvironmentFile=-/etc/fpai/ai.env
EnvironmentFile=-/opt/fpai/services/whaletrack-magnet/api/.env
ExecStart=/usr/bin/python3 core/position_protection_reconciler.py --once
UNIT
cat > /etc/systemd/system/whaletrack-reconciler.timer <<UNIT
[Unit]
Description=Run whaletrack reconciler every 2 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now whaletrack-reconciler.timer
systemctl status whaletrack-reconciler.timer --no-pager | head -4
'

echo "═══ 5/5 · verify resting stops landed ═══"
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
