#!/bin/bash
# Adam's daily opportunity scanner
# Purpose: Proactively surface 3 concrete things Adam can help with
# Cost: ~$0.05-0.10/day (1 claude-sonnet call, ~2k input / 500 output tokens)
# Silent if nothing worth surfacing
#
# Signals gathered (all free):
#   1. NOW.md unchecked items
#   2. Last 48h of James<->Adam Telegram exchanges (what James has been asking)
#   3. Days since MEMORY.md last touched
#   4. zv-telegram-bot recent activity (guest/team signals)
#   5. Yesterday's P&L from adam_daily_value.log
#   6. Brain Mesh brief (ZV + Sunheart + brain health via brain-brief.sh)
#
# Outputs:
#   - Telegram message to James (free)
#   - Log to /opt/fpai/logs/opportunities.jsonl (one JSON per scan)

set -e
umask 077

LOG_JSONL=/opt/fpai/logs/opportunities.jsonl
WORKSPACE=/opt/fpai/openclaw/workspace
NOW_MD=$WORKSPACE/NOW.md
MEMORY_MD=$WORKSPACE/MEMORY.md
DAILY_LOG=/opt/fpai/logs/adam_daily_value.log
SCAN_DATE=$(date -u +"%Y-%m-%d")
SCAN_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ============================================================
# 1) Gather cheap signals
# ============================================================

# A. NOW.md context - unchecked priority items
UNCHECKED=$(awk '/^## PRIORITIES/,/^## (DEFAULT MOTION|DIVISION OF LABOR|DONE|$)/' "$NOW_MD" 2>/dev/null | grep -E '^- \[ \]' | head -15)
NOW_EXCERPT=$(awk '/^## (NOW|ONE ENGINE|PRIORITIES|DIVISION)/,/^##/' "$NOW_MD" 2>/dev/null | head -80)

# B. Recent Adam<->James Telegram messages (last 48h)
TODAY_LOG="/tmp/openclaw/openclaw-${SCAN_DATE}.log"
YESTERDAY_LOG="/tmp/openclaw/openclaw-$(date -u -d 'yesterday' +%Y-%m-%d 2>/dev/null || date -u -v-1d +%Y-%m-%d).log"
RECENT_JAMES=""
for f in "$TODAY_LOG" "$YESTERDAY_LOG"; do
  [ -f "$f" ] && RECENT_JAMES="$RECENT_JAMES$(grep -iE 'messageChannel=(telegram|whatsapp)' "$f" 2>/dev/null | grep -oE '"text":"[^"]{5,400}"' | head -20)"
done
[ -z "$RECENT_JAMES" ] && RECENT_JAMES="(no James messages in last 48h)"

# C. MEMORY.md staleness
MEMORY_AGE_HOURS=0
if [ -f "$MEMORY_MD" ]; then
  MEM_MTIME=$(stat -c %Y "$MEMORY_MD" 2>/dev/null || stat -f %m "$MEMORY_MD" 2>/dev/null)
  NOW_TS=$(date +%s)
  MEMORY_AGE_HOURS=$(( (NOW_TS - MEM_MTIME) / 3600 ))
fi

# D. zv-telegram-bot activity (what the ground team has been doing)
ZV_ACTIVITY=$(journalctl -u zv-telegram-bot --since "48 hours ago" --no-pager 2>/dev/null | grep -iE "intent|task|note|query" | tail -10 || true)
[ -z "$ZV_ACTIVITY" ] && ZV_ACTIVITY="(zv bot idle or inaccessible)"

# E. Yesterday's P&L
YESTERDAY_PNL=$(tail -5 "$DAILY_LOG" 2>/dev/null | grep -E "^20[0-9]{2}-" | tail -2 || echo "(no P&L history)")


# F. ZV BRAIN PULL - Adam can now see the actual ZV state (NEW 2026-04-24)
ZV_STATUS=$(/opt/fpai/openclaw/workspace/tools/zv-brain.sh status 2>/dev/null | head -20 || echo "(zv-brain unavailable)")
ZV_OPEN_MASTER=$(/opt/fpai/openclaw/workspace/tools/zv-brain.sh list master_list 10 2>/dev/null | python3 -c "
import json, sys
try:
    rows = json.load(sys.stdin)
    open_rows = [r for r in rows if not r.get('Done') and r.get('Status') != 'Done']
    for r in open_rows[:5]:
        title = r.get('Title') or r.get('Name') or '(untitled)'
        pri = r.get('Priority','')
        print(f'  [{pri}] {title[:80]}')
except: pass
" 2>/dev/null)
[ -z "$ZV_OPEN_MASTER" ] && ZV_OPEN_MASTER="(no open master list items)"

# G. ZV TELEGRAM SIGNALS - what the ground team has been doing (NEW)
ZV_SIGNALS=$(/opt/fpai/openclaw/workspace/tools/zv-signals.sh 48 2>/dev/null | head -20 || echo "(no zv-signals)")

# H. Brain Mesh brief — one HTTP round-trip (read-only adapters)
BRAIN_BRIEF="(brain-brief unavailable)"
BB_OUT=$("$WORKSPACE/infrastructure/tools/brain-brief.sh" "today updates blockers opportunities" 2>/dev/null) || true
if [ -n "$BB_OUT" ]; then
  BRAIN_BRIEF=$(printf '%s' "$BB_OUT" | python3 -c "
import json, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw)
    print(json.dumps(d, ensure_ascii=False)[:4500])
except Exception:
    print(raw[:4500])
" 2>/dev/null) || BRAIN_BRIEF=$(printf '%s' "$BB_OUT" | head -c 4500)
fi

# ============================================================
# 2) Build the Claude prompt (bounded context)
# ============================================================
read -r -d '' PROMPT <<EOF || true
You are Adam, an AI agent whose job is Telegram relay to James for Zen Village engine.

Scan the signals below and produce the TOP 3 concrete opportunities where YOU can help James this week. Each opportunity must be:
  - ZV-aligned (advances PROOF > REVENUE > CLARITY > EASE)
  - Something you can actually execute (draft copy, summarize, research, organize, template)
  - Small enough to complete in <2 hours of Adam-time
  - Framed as a specific deliverable James can say "yes" or "no" to

OUTPUT FORMAT (strict):
Opportunity 1: [one-line title]
  What: [1 sentence: the deliverable]
  Why now: [1 sentence: what signal prompted this]
  Time: [estimate, e.g. "~30 min"]

Opportunity 2: ...
Opportunity 3: ...

Ask James: [one line question to greenlight which to start with]

---SIGNALS---

[NOW.md excerpt]
$NOW_EXCERPT

[Unchecked priorities]
$UNCHECKED

[James messages last 48h (may be noisy/log-ish — extract real asks only)]
$RECENT_JAMES

[MEMORY.md age]
$MEMORY_AGE_HOURS hours since last update

[ZV ground-team bot activity last 48h]
$ZV_ACTIVITY

[ZV Brain open Master List items - WHAT JAMES ACTUALLY HAS ON HIS PLATE]
$ZV_OPEN_MASTER

[ZV Brain DB row counts (7 DBs)]
$ZV_STATUS

[ZV Telegram signals - who said what to zv-brain bot last 48h]
$ZV_SIGNALS

[Brain Mesh brief — ZV search + Sunheart + per-brain health]
$BRAIN_BRIEF

[Yesterday P&L]
$YESTERDAY_PNL

---
Remember: if no real opportunities exist, say so. Output "NONE — keeping quiet today." Token silence is valid.
EOF

# ============================================================
# 3) Call Claude (one call only)
# ============================================================
RESPONSE=$(curl -s --max-time 90 http://127.0.0.1:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json, sys
p = sys.stdin.read()
print(json.dumps({
  'model': 'claude-sonnet-4-5',
  'max_tokens': 800,
  'messages': [{'role': 'user', 'content': p}]
}))
" <<< "$PROMPT")" 2>/dev/null)

# Extract text
TEXT=$(echo "$RESPONSE" | python3 -c "
import json, sys
try:
  d = json.load(sys.stdin)
  if 'choices' in d and isinstance(d['choices'], list) and d['choices']:
    print(d['choices'][0].get('message',{}).get('content','').strip())
  elif 'error' in d:
    print('ERROR:', d['error'].get('message',str(d['error'])))
  else:
    print('ERROR: unexpected response')
except Exception as e:
  print('ERROR parsing:', e)
" 2>/dev/null)

# ============================================================
# 4) Decide: silent or notify
# ============================================================
if [ -z "$TEXT" ] || echo "$TEXT" | grep -q "^ERROR"; then
  echo "{\"timestamp\":\"$SCAN_TIME\",\"status\":\"error\",\"detail\":$(echo "$TEXT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')}" >> "$LOG_JSONL"
  exit 1
fi

if echo "$TEXT" | grep -qi "^NONE\|keeping quiet"; then
  echo "{\"timestamp\":\"$SCAN_TIME\",\"status\":\"silent\",\"reason\":\"nothing to surface\"}" >> "$LOG_JSONL"
  exit 0
fi

# ============================================================
# 5) Send to James via Telegram
# ============================================================
TOKEN=$(python3 -c "
import json
d = json.load(open('/root/.openclaw/openclaw.json'))
def find(o):
    if isinstance(o, dict):
        for k,v in o.items():
            if 'telegram' in k.lower() and isinstance(v,dict):
                t = v.get('botToken') or v.get('token')
                if t: print(t); return
            find(v)
    elif isinstance(o,list):
        for i in o: find(i)
find(d)
" 2>/dev/null | head -1)

CHAT=$(grep -oE 'TELEGRAM_CHAT_ID=[0-9]+' /opt/fpai/cora-loop/.env 2>/dev/null | cut -d= -f2 | head -1)
[ -z "$CHAT" ] && CHAT=8514069423  # James' known chat id

MSG="Good morning. I scanned your world and found things I could help with:

$TEXT

— Adam (reply with the number to greenlight)"

if [ -n "$TOKEN" ] && [ -n "$CHAT" ]; then
  curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
    -d "chat_id=$CHAT" \
    --data-urlencode "text=$MSG" > /tmp/adam-opp-send.json
  SENT=$(python3 -c "import json; d=json.load(open('/tmp/adam-opp-send.json')); print(d.get('ok'))" 2>/dev/null)
else
  SENT="missing_creds"
fi

echo "{\"timestamp\":\"$SCAN_TIME\",\"status\":\"sent\",\"telegram_ok\":\"$SENT\",\"opportunities\":$(python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' <<< "$TEXT")}" >> "$LOG_JSONL"

exit 0
