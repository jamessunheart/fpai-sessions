#!/bin/bash
# OneBPO Overflow Channel — Route tasks to Alice's team
# Usage:
#   overflow.sh send <urgency> <title> <instructions>
#   overflow.sh queue                     — show pending overflow items
#   overflow.sh status                    — overflow channel health

: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN must be set in env (see /opt/fpai/.env)}"
: "${SUNHEART_CHAT_ID:?SUNHEART_CHAT_ID must be set in env (see /opt/fpai/.env)}"
OVERFLOW_DIR="/opt/fpai/overflow"
QUEUE_FILE="$OVERFLOW_DIR/queue.jsonl"

mkdir -p "$OVERFLOW_DIR"

send_telegram() {
    local CHAT_ID="$1" MSG="$2"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\":\"$CHAT_ID\",\"text\":$(python3 -c "import json; print(json.dumps('''$MSG'''))")}" > /dev/null
}

cmd_send() {
    local URGENCY="$1" TITLE="$2" INSTRUCTIONS="$3"
    [ -z "$URGENCY" ] || [ -z "$TITLE" ] || [ -z "$INSTRUCTIONS" ] && {
        echo "Usage: overflow.sh send <today|this_week|when_possible> <title> <instructions>"
        return 1
    }
    
    local ID="ovf_$(date +%s)"
    local TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    echo "{\"id\":\"$ID\",\"ts\":\"$TS\",\"urgency\":\"$URGENCY\",\"title\":\"$TITLE\",\"status\":\"pending\"}" >> "$QUEUE_FILE"
    
    local MSG="OVERFLOW TASK [$URGENCY]

Title: $TITLE

Instructions for OneBPO:
$INSTRUCTIONS

---
Task ID: $ID
Assigned: OneBPO / Alice
Reply with status update when done."
    
    send_telegram "$SUNHEART_CHAT_ID" "$MSG"
    
    echo "Overflow task $ID queued and sent to Telegram"
    echo "  Urgency: $URGENCY"
    echo "  Title: $TITLE"
}

cmd_queue() {
    if [ -f "$QUEUE_FILE" ]; then
        echo "Pending overflow tasks:"
        python3 -c "
import json, sys
for line in open('$QUEUE_FILE'):
    try:
        d = json.loads(line.strip())
        status = d.get('status','?')
        icon = {'pending':'   ','done':'   ','cancelled':'   '}.get(status,'?')
        print(f\"  {icon} [{d['urgency']:13s}] {d['title']} ({d['id']})\")
    except: pass
"
    else
        echo "No overflow tasks yet."
    fi
}

cmd_status() {
    echo "Overflow Channel Status"
    echo "  Queue file: $QUEUE_FILE"
    if [ -f "$QUEUE_FILE" ]; then
        TOTAL=$(wc -l < "$QUEUE_FILE")
        echo "  Total tasks: $TOTAL"
    else
        echo "  Total tasks: 0"
    fi
    echo "  Delivery: Telegram to Sunheart (who forwards to Alice)"
    echo "  Channel: Active"
}

case "${1:-}" in
    send)   cmd_send "$2" "$3" "$4" ;;
    queue)  cmd_queue ;;
    status) cmd_status ;;
    *)      echo "OneBPO Overflow Channel"; echo "  send <urgency> <title> <instructions>"; echo "  queue  — pending items"; echo "  status — channel health" ;;
esac
