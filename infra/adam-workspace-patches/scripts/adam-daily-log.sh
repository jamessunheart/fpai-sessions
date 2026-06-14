#!/bin/bash
# Nightly 23:59 UTC: Adam P&L for the day
DATE=$(date -u +%Y-%m-%d)
LOG=/opt/fpai/logs/adam_daily_value.log
TODAY_LOG="/tmp/openclaw/openclaw-${DATE}.log"

CLAUDE_CALLS=0
TG_MESSAGES=0
WA_MESSAGES=0
CRON_CALLS=0
HEARTBEAT_CALLS=0

if [ -f "$TODAY_LOG" ]; then
  CLAUDE_CALLS=$(grep -cE "provider=metaclaw|model=claude-sonnet" "$TODAY_LOG" 2>/dev/null)
  TG_MESSAGES=$(grep -c "messageChannel=telegram" "$TODAY_LOG" 2>/dev/null)
  WA_MESSAGES=$(grep -c "messageChannel=whatsapp" "$TODAY_LOG" 2>/dev/null)
  CRON_CALLS=$(grep -c "messageChannel=cron-event" "$TODAY_LOG" 2>/dev/null)
  HEARTBEAT_CALLS=$(grep -c "messageChannel=heartbeat" "$TODAY_LOG" 2>/dev/null)
fi

OLLAMA_CALLS=$(grep -c "$DATE" /opt/fpai/logs/ollama-calls.log 2>/dev/null)
JAMES_INTERACTIONS=$((TG_MESSAGES + WA_MESSAGES))

# Cost: $0.03/call, compute via awk to avoid quoting issues
EST_COST=$(awk -v n=$CLAUDE_CALLS "BEGIN{printf \"%.2f\", n*0.03}")

ALERT=""
if [ "$CLAUDE_CALLS" -gt 50 ] && [ "$JAMES_INTERACTIONS" -lt 1 ]; then
  ALERT=" [SELF-THROTTLE: no James interaction today]"
fi
if [ "$CLAUDE_CALLS" -gt 100 ]; then
  ALERT="$ALERT [HIGH-BURN]"
fi

echo "$DATE | claude=$CLAUDE_CALLS \$$EST_COST | ollama=$OLLAMA_CALLS \$0 | james_tg=$TG_MESSAGES wa=$WA_MESSAGES | cron=$CRON_CALLS heartbeat=$HEARTBEAT_CALLS$ALERT" >> "$LOG"

ROIDER=/opt/fpai/openclaw/workspace/infrastructure/tools/adam-roi-ledger.sh
if [ -x "$ROIDER" ]; then
  "$ROIDER" || true
fi
