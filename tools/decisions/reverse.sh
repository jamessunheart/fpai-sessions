#!/usr/bin/env bash
# Reverse a logged decision · v1 · 2026-05-24
# Usage: reverse.sh <decision_id> [reason]
#
# Marks the decision as REVERSED in ~/.config/fpai/decisions/log.jsonl
# AND prints the rollback_cmd for manual or auto-execution.
#
# This script does NOT auto-execute the rollback unless --execute flag passed.
set -euo pipefail

LOG="$HOME/.config/fpai/decisions/log.jsonl"

if [[ ! -f "$LOG" ]]; then
  echo "ERROR: log not found at $LOG" >&2
  exit 1
fi

DECISION_ID="${1:-}"
if [[ -z "$DECISION_ID" ]]; then
  echo "Usage: $0 <decision_id> [reason] [--execute]" >&2
  echo "" >&2
  echo "Recent decisions:" >&2
  tail -10 "$LOG" | python3 -c "
import json, sys
for line in sys.stdin:
    try:
        d = json.loads(line)
        print(f\"  {d.get('decision_id'):20s} {d.get('reversal_status','?'):10s} {d.get('topic','')[:70]}\")
    except: pass
" >&2
  exit 2
fi

shift
REASON="${1:-no reason given}"
EXECUTE=false
if [[ "${1:-}" == "--execute" ]] || [[ "${2:-}" == "--execute" ]]; then
  EXECUTE=true
fi

# Find decision in log, flip reversal_status, append updated entry (don't mutate history)
python3 - <<PY
import json, sys
from pathlib import Path
from datetime import datetime, timezone

log_file = Path("$LOG")
target = "$DECISION_ID"
reason = """$REASON"""
execute = $( $EXECUTE && echo "True" || echo "False" )

found = None
for line in log_file.read_text().splitlines():
    if not line.strip():
        continue
    try:
        e = json.loads(line)
        if e.get("decision_id") == target:
            found = e
    except: pass

if not found:
    print(f"ERROR: decision_id '{target}' not found in log", file=sys.stderr)
    sys.exit(3)

if found.get("reversal_status") == "REVERSED":
    print(f"NOTE: decision {target} already marked REVERSED at {found.get('reversed_at')}", file=sys.stderr)

# Append a REVERSAL_EVENT record (immutable log discipline — never mutate, only append)
reversal = {
    "event_type": "REVERSAL",
    "decision_id": target,
    "reversal_timestamp": datetime.now(timezone.utc).isoformat(),
    "reversed_by": "james",
    "reason": reason,
    "original_topic": found.get("topic"),
    "original_synthesis_preview": (found.get("synthesis") or "")[:200],
    "rollback_cmd": found.get("rollback_cmd"),
    "rollback_executed": execute,
}

with open(log_file, "a") as f:
    f.write(json.dumps(reversal) + "\n")

print(f"REVERSAL logged for {target}")
print(f"  reason: {reason}")
print(f"  rollback_cmd: {found.get('rollback_cmd') or '(none specified at decision time)'}")
if execute and found.get("rollback_cmd"):
    print(f"  EXECUTING rollback_cmd...")
PY

if [[ "$EXECUTE" == "true" ]]; then
  # Re-extract rollback_cmd safely and execute
  ROLLBACK_CMD="$(python3 -c "
import json
from pathlib import Path
log = Path('$LOG').read_text().splitlines()
for line in log:
    try:
        e = json.loads(line)
        if e.get('decision_id') == '$DECISION_ID' and not e.get('event_type'):
            print(e.get('rollback_cmd', ''))
            break
    except: pass
")"
  if [[ -n "$ROLLBACK_CMD" ]]; then
    echo ""
    echo "=== executing rollback_cmd ==="
    echo "+ $ROLLBACK_CMD"
    eval "$ROLLBACK_CMD"
    echo "=== rollback complete ==="
  else
    echo "WARN: no rollback_cmd recorded for this decision · manual reversal required" >&2
  fi
fi
