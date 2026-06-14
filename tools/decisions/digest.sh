#!/usr/bin/env bash
# Decision-log daily digest · v1 · 2026-05-24
# Reads ~/.config/fpai/decisions/log.jsonl, formats last 24hr of decisions,
# prints to stdout. Pipe to Telegram or read manually.
#
# Usage:
#   bash digest.sh                  # show today's decisions
#   bash digest.sh --since 48h      # last 48 hours
#   bash digest.sh --all-open       # only decisions where reversal_status=OPEN
set -euo pipefail

LOG="$HOME/.config/fpai/decisions/log.jsonl"
if [[ ! -f "$LOG" ]]; then
  echo "No decision log at $LOG"
  exit 0
fi

SINCE="${1:-24h}"
if [[ "$SINCE" == "--all-open" ]]; then
  MODE="all-open"
  SINCE_SECONDS=999999999
else
  MODE="since"
  # Parse --since flag value
  if [[ "${1:-}" == "--since" ]]; then SINCE="${2:-24h}"; fi
  case "$SINCE" in
    *h) SINCE_SECONDS=$(( ${SINCE%h} * 3600 )) ;;
    *d) SINCE_SECONDS=$(( ${SINCE%d} * 86400 )) ;;
    *)  SINCE_SECONDS=$(( 24 * 3600 )) ;;
  esac
fi

python3 - <<PY
import json, sys, time
from datetime import datetime, timezone
from pathlib import Path

log_file = Path("$LOG")
since_sec = $SINCE_SECONDS
mode = "$MODE"
now = time.time()

decisions = []
reversals = {}
for line in log_file.read_text().splitlines():
    if not line.strip():
        continue
    try:
        e = json.loads(line)
    except json.JSONDecodeError:
        continue
    if e.get("event_type") == "REVERSAL":
        reversals[e["decision_id"]] = e
    else:
        # Decision entry
        try:
            ts = datetime.fromisoformat(e["started_at"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            ts = 0
        e["_ts"] = ts
        decisions.append(e)

# Filter
if mode == "all-open":
    decisions = [d for d in decisions if d.get("reversal_status", "OPEN") == "OPEN"]
else:
    decisions = [d for d in decisions if (now - d["_ts"]) <= since_sec]

decisions.sort(key=lambda d: d["_ts"], reverse=True)

print("=" * 70)
print(f"📋 DECISION DIGEST · {datetime.now(timezone.utc).isoformat()[:19]}Z")
if mode == "all-open":
    print(f"   Showing all OPEN (un-reversed) decisions")
else:
    print(f"   Showing decisions from last {int(since_sec/3600)}h")
print(f"   Log: {log_file}")
print("=" * 70)
print()

if not decisions:
    print("(no decisions in window)")
else:
    for d in decisions:
        rev = reversals.get(d["decision_id"])
        status_icon = "↩ REVERSED" if rev else "✓ OPEN"
        cost = d.get("total_cost_usd", 0)
        topic = d.get("topic", "(no topic)")
        if len(topic) > 200:
            topic = topic[:200] + "..."

        # Extract recommendation from synthesis
        synth = d.get("synthesis", "") or ""
        rec = ""
        for line in synth.split("\n"):
            if "**Recommendation" in line or "Recommendation:" in line:
                rec = line.strip().replace("**", "")
                break

        print(f"━━ {d['decision_id']} · {status_icon} · \${cost:.2f} ━━")
        print(f"📝 {topic}")
        if rec:
            print(f"⚖  {rec[:200]}")
        if rev:
            print(f"↩  Reversed at {rev['reversal_timestamp'][:19]} · reason: {rev.get('reason','no reason')[:80]}")
        print(f"🔧 Reverse: bash tools/decisions/reverse.sh {d['decision_id']} \"reason\" [--execute]")
        print()

print("=" * 70)
PY

if [[ -n "${EMBER_DIGEST_TG:-}" ]]; then
  echo ""
  echo "(would push to Telegram channel $EMBER_DIGEST_CHANNEL — not yet wired)"
fi
