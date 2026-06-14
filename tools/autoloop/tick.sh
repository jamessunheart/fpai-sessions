#!/usr/bin/env bash
# autoloop tick — the self-standing engine running unattended, WITHIN COST CONSTRAINTS.
# James blessed "go autonomous within cost constraints" 2026-06-06. Guided by vault ALIGNMENT.
# Per tick: (1) cost-guard + kill-switch, (2) closeout reconciles all surfaces (live, ~$0),
#           (3) router reports the next AI-doable step (report-only — writes nothing yet).
# MAY NOT: move money/deploy/secrets/delete/public — router escalates gated work, never acts on it.
#   Kill:    touch ~/.config/fpai/cost/.pause-ambient   (halts all ambient loops)
#   Disable: touch ~/.config/fpai/autoloop/.disabled
set -u
CFG="$HOME/.config/fpai/autoloop"; mkdir -p "$CFG"
LOG="$CFG/runs.log"
REPO="$HOME/FPAI_Cockpit"
export FPAI_VAULT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/FPOS/Full Potential OS"
PY="$(command -v python3 || echo /usr/bin/python3)"

[ -f "$CFG/.disabled" ] && { echo "$(date) disabled" >>"$LOG"; exit 0; }
"$HOME/.local/bin/cost-guard" autoloop || { echo "$(date) cost-guard blocked" >>"$LOG"; exit 0; }
cd "$REPO" 2>/dev/null || { echo "$(date) ERROR no repo" >>"$LOG"; exit 0; }

{
  echo "=== $(date) autoloop tick ==="
  "$PY" tools/closeout/run.py 2>&1 | sed 's/^/  closeout: /'
  echo "  --- router (report-only) ---"
  "$PY" tools/router/route.py 2>&1 | grep -E "^(intent|title|action|detail|gate)" | sed 's/^/  router: /'
} >>"$LOG" 2>&1
echo "$(date) tick done" >>"$LOG"
