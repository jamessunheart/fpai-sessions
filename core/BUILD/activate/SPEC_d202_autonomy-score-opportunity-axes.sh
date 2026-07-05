#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FPAI_REPO_ROOT:-/opt/fpai-build/FPAI_Cockpit}"
UNIT_DIR="${FPAI_SYSTEMD_DIR:-/etc/systemd/system}"
SERVICE_NAME="fpai-opportunity-axis-scorer.service"
TIMER_NAME="fpai-opportunity-axis-scorer.timer"
KILL_SWITCH="${FPAI_OPPORTUNITY_AXIS_SCORER_KILL_SWITCH:-/opt/fpai-build/.opportunity_axis_scorer_disabled}"
LEDGER="${FPAI_OPPORTUNITY_LEDGER:-/root/.config/fpai/allocation/opportunities.json}"
LOG_PATH="${FPAI_OPPORTUNITY_AXIS_SCORE_LOG:-/root/.config/fpai/allocation/opportunity_axis_scores.jsonl}"

mkdir -p "$UNIT_DIR"

cat >"$UNIT_DIR/$SERVICE_NAME" <<UNIT
[Unit]
Description=FPAI advisory opportunity axis scorer
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$REPO_ROOT
Environment=FPAI_OPPORTUNITY_LEDGER=$LEDGER
Environment=FPAI_OPPORTUNITY_AXIS_SCORE_LOG=$LOG_PATH
ExecStart=/bin/bash -lc 'if test -f "$KILL_SWITCH"; then echo "opportunity axis scorer disabled by $KILL_SWITCH"; exit 0; fi; python3 tools/allocation/opportunity_axis_scorer.py --ledger "\$FPAI_OPPORTUNITY_LEDGER" --log "\$FPAI_OPPORTUNITY_AXIS_SCORE_LOG" --rescore-all --json'
UNIT

cat >"$UNIT_DIR/$TIMER_NAME" <<UNIT
[Unit]
Description=Run FPAI advisory opportunity axis scorer every 6 hours

[Timer]
OnBootSec=20min
OnUnitActiveSec=6h
Persistent=true
RandomizedDelaySec=10min

[Install]
WantedBy=timers.target
UNIT

if command -v systemctl >/dev/null 2>&1 && [[ "$UNIT_DIR" == "/etc/systemd/system" ]]; then
  systemctl daemon-reload
  systemctl enable --now "$TIMER_NAME"
  systemctl list-timers "$TIMER_NAME" --no-pager || true
else
  echo "systemd activation skipped; units written to $UNIT_DIR"
fi

echo "installed $TIMER_NAME; scorer is advisory, writes axes/log only, kill switch: $KILL_SWITCH"
