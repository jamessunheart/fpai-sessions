#!/bin/bash
# Append one structured JSON line per day for cost vs. engagement (ROI ledger).
# Run once daily after adam-daily-log.sh (same metric sources).
set -euo pipefail

DATE=$(date -u +%Y-%m-%d)
ISO_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LOG_JSONL=/opt/fpai/logs/adam_roi.jsonl
TODAY_LOG="/tmp/openclaw/openclaw-${DATE}.log"

CLAUDE_CALLS=0
TG_MESSAGES=0
WA_MESSAGES=0
CRON_CALLS=0
HEARTBEAT_CALLS=0

if [ -f "$TODAY_LOG" ]; then
  CLAUDE_CALLS=$(grep -cE "provider=metaclaw|model=claude-sonnet" "$TODAY_LOG" 2>/dev/null || true)
  TG_MESSAGES=$(grep -c "messageChannel=telegram" "$TODAY_LOG" 2>/dev/null || true)
  WA_MESSAGES=$(grep -c "messageChannel=whatsapp" "$TODAY_LOG" 2>/dev/null || true)
  CRON_CALLS=$(grep -c "messageChannel=cron-event" "$TODAY_LOG" 2>/dev/null || true)
  HEARTBEAT_CALLS=$(grep -c "messageChannel=heartbeat" "$TODAY_LOG" 2>/dev/null || true)
fi

OLLAMA_CALLS=0
if [ -f /opt/fpai/logs/ollama-calls.log ]; then
  OLLAMA_CALLS=$(grep -c "$DATE" /opt/fpai/logs/ollama-calls.log 2>/dev/null || true)
fi
JAMES_INTERACTIONS=$((TG_MESSAGES + WA_MESSAGES))
EST_COST=$(awk -v n="$CLAUDE_CALLS" 'BEGIN{printf "%.4f", n*0.03}')

ALERTS=""
if [ "$CLAUDE_CALLS" -gt 50 ] && [ "$JAMES_INTERACTIONS" -lt 1 ]; then
  ALERTS="${ALERTS}self_throttle_no_james "
fi
if [ "$CLAUDE_CALLS" -gt 100 ]; then
  ALERTS="${ALERTS}high_burn "
fi

if [ "$CLAUDE_CALLS" -gt 0 ]; then
  ROI_RATIO=$(awk -v j="$JAMES_INTERACTIONS" -v c="$CLAUDE_CALLS" 'BEGIN{printf "%.6f", j/c}')
else
  ROI_RATIO=""
fi

mkdir -p "$(dirname "$LOG_JSONL")"
umask 077
export ISO_TS DATE CLAUDE_CALLS EST_COST OLLAMA_CALLS TG_MESSAGES WA_MESSAGES CRON_CALLS HEARTBEAT_CALLS JAMES_INTERACTIONS ROI_RATIO ALERTS
python3 <<'PY'
import json, os

def num(name, default=0):
    v = os.environ.get(name, "")
    try:
        return int(v) if "." not in v else float(v)
    except ValueError:
        return default

ratio_raw = os.environ.get("ROI_RATIO", "").strip()
if ratio_raw == "":
    value_proxy = None
else:
    try:
        value_proxy = float(ratio_raw)
    except ValueError:
        value_proxy = None

row = {
    "schema": "adam_roi_v1",
    "ts_utc": os.environ["ISO_TS"],
    "date": os.environ["DATE"],
    "claude_calls": num("CLAUDE_CALLS"),
    "est_cost_usd": float(os.environ.get("EST_COST", "0") or 0),
    "ollama_calls": num("OLLAMA_CALLS"),
    "telegram_messages": num("TG_MESSAGES"),
    "whatsapp_messages": num("WA_MESSAGES"),
    "cron_messages": num("CRON_CALLS"),
    "heartbeat_messages": num("HEARTBEAT_CALLS"),
    "james_interactions": num("JAMES_INTERACTIONS"),
    "value_proxy_james_per_claude_call": value_proxy,
    "alerts": (os.environ.get("ALERTS") or "").strip(),
}
path = "/opt/fpai/logs/adam_roi.jsonl"
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
PY
