#!/usr/bin/env bash
# Ember ambient responder · v1 · 2026-05-24
# Fires every N minutes via LaunchAgent · reads inbox · spawns claude -p · sends reply to TG
# Kill: touch ~/.config/fpai/tg_inbox/.responder_disabled
# Cost cap: $1/spawn · monitored externally via daily digest
set -euo pipefail

# Cost-guard (2026-05-31): skip this tick if paused / over metered $/day / over daily run cap.
# Kill: touch ~/.config/fpai/cost/.pause-ambient · see WHAT RUNS WITHOUT ME.
"$HOME/.local/bin/cost-guard" responder || exit 0

# === Paths ===
HOME_DIR="${HOME:-/Users/jamessunheart}"
INBOX="$HOME_DIR/.config/fpai/tg_inbox/messages.jsonl"
LAST_READ="$HOME_DIR/.config/fpai/tg_inbox/last_responder_read.txt"
DISABLE_FLAG="$HOME_DIR/.config/fpai/tg_inbox/.responder_disabled"
LOG="$HOME_DIR/.config/fpai/decisions/log.jsonl"
PROMPT_TEMPLATE="/Users/jamessunheart/FPAI_Cockpit/tools/decisions/ember_responder_prompt.md"
CLAUDE_BIN="$HOME_DIR/.local/bin/claude"
SEND_DIGEST="/Users/jamessunheart/FPAI_Cockpit/tools/decisions/send_tg_digest.py"

# === Path setup for cron-style env ===
export PATH="$HOME_DIR/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# === Kill switch ===
if [[ -f "$DISABLE_FLAG" ]]; then
  echo "[$(date -Iseconds)] responder DISABLED via flag, exiting"
  exit 0
fi

# === Anything to do? ===
if [[ ! -f "$INBOX" ]]; then
  exit 0
fi

LAST_ID=0
if [[ -f "$LAST_READ" ]]; then
  LAST_ID="$(cat "$LAST_READ" 2>/dev/null || echo 0)"
fi

# Find newest inbox entry's update_id
NEWEST_ID=$(python3 -c "
import json, sys
from pathlib import Path
p = Path('$INBOX')
if not p.exists():
    print(0)
    sys.exit(0)
maxid = 0
for line in p.read_text().splitlines():
    if not line.strip():
        continue
    try:
        e = json.loads(line)
        uid = e.get('update_id', 0)
        if uid > maxid:
            maxid = uid
    except: pass
print(maxid)
" 2>/dev/null || echo 0)

if [[ "$NEWEST_ID" -le "$LAST_ID" ]]; then
  exit 0  # nothing new
fi

echo "[$(date -Iseconds)] new messages detected · last=$LAST_ID newest=$NEWEST_ID · spawning Ember"

# === Build the response prompt ===
# Extract NEW inbox entries (update_id > LAST_ID), format as context
NEW_ENTRIES=$(python3 -c "
import json
from pathlib import Path
p = Path('$INBOX')
entries = []
for line in p.read_text().splitlines():
    if not line.strip():
        continue
    try:
        e = json.loads(line)
        if e.get('update_id', 0) > $LAST_ID:
            entries.append(e)
    except: pass

for e in entries:
    t = e.get('type', '?')
    text = e.get('text', '(no text)')
    ts = e.get('received_at', '')[:19]
    dur = e.get('duration_s', '')
    if t == 'voice':
        print(f'[{ts}] VOICE NOTE ({dur}s): {text}')
    elif t == 'text':
        print(f'[{ts}] TEXT: {text}')
    else:
        print(f'[{ts}] {t.upper()}: {text}')
")

# === Smart-loop context (intent queue + rolling history) ===
# Use single-quoted python -c with env-var passing to avoid bash interpreting Python f-strings

INTENT_QUEUE_FILE="$HOME_DIR/.config/fpai/intent_queue/queue.jsonl"

INTENT_QUEUE_CONTEXT=$(INTENT_FILE="$INTENT_QUEUE_FILE" python3 -c '
import os, json
from pathlib import Path
p = Path(os.environ["INTENT_FILE"])
if not p.exists() or not p.read_text().strip():
    print("(intent queue is empty · no in-flight intents)")
else:
    open_intents = []
    for line in p.read_text().splitlines():
        if not line.strip(): continue
        try:
            e = json.loads(line)
            if e.get("status", "open") in ("open", "in_progress"):
                open_intents.append(e)
        except: pass
    if not open_intents:
        print("(intent queue has no open items)")
    else:
        for e in open_intents[-15:]:
            sid = e.get("intent_id", "?")
            st = e.get("status", "open")
            desc = (e.get("description") or "")[:160]
            cb = e.get("created_by", "?")
            print(f"  [{sid}] {st} by {cb}: {desc}")
' 2>/dev/null)

RECENT_DECISIONS=$(LOG_FILE="$LOG" python3 -c '
import os, json
from pathlib import Path
p = Path(os.environ["LOG_FILE"])
if not p.exists():
    print("(no decision log yet)")
else:
    lines = p.read_text().splitlines()[-10:]
    for line in lines:
        if not line.strip(): continue
        try:
            e = json.loads(line)
            et = e.get("event_type", "decision")
            ts = (e.get("timestamp") or e.get("started_at") or "")[:19]
            did = (e.get("decision_id") or "")[:24]
            if et == "decision":
                cost = e.get("total_cost_usd", 0)
                summary = (e.get("ember_summary") or e.get("topic") or "")[:100]
                print(f"  {ts} DECISION {did} · ${cost:.2f} · {summary}")
            elif et == "ACTIONS_TAKEN":
                n = len(e.get("actions", []))
                sa = (e.get("sub_action") or "")[:80]
                print(f"  {ts} ACTIONS for {did} · {n} action(s) · {sa}")
            elif et == "REVERSAL":
                reason = (e.get("reason") or "")[:80]
                print(f"  {ts} REVERSAL of {did} · {reason}")
            elif et in ("AMBIENT_RESPONDER_RUN", "AMBIENT_RESPONDER_FAILURE"):
                np = e.get("newest_processed") or e.get("newest_seen") or ""
                print(f"  {ts} {et} · last_read→{np}")
            else:
                print(f"  {ts} {et}")
        except: pass
' 2>/dev/null)

RECENT_NARRATORS=$(ls -t /Users/jamessunheart/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/sessions/2026-*.md 2>/dev/null | head -3 | python3 -c '
import sys
for path in sys.stdin.read().strip().splitlines():
    if not path: continue
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("# "):
                    fname = path.split("/")[-1]
                    print(f"  {fname}: {line[2:].strip()}")
                    break
    except: pass
' 2>/dev/null)

if [[ -z "$NEW_ENTRIES" ]]; then
  echo "[$(date -Iseconds)] no extractable new entries · updating marker · exit"
  echo "$NEWEST_ID" > "$LAST_READ"
  exit 0
fi

# Load prompt template + inject new entries
PROMPT=$(cat "$PROMPT_TEMPLATE" 2>/dev/null)
if [[ -z "$PROMPT" ]]; then
  echo "[$(date -Iseconds)] FATAL: prompt template missing at $PROMPT_TEMPLATE"
  exit 1
fi

FULL_PROMPT=$(printf '%s\n\n## SUBSTRATE CONTEXT FOR THIS CYCLE\n\n### Intent Queue (in-flight intents that persist across spawns)\n\n%s\n\n### Recent Decision Log (last 10 events · compact)\n\n%s\n\n### Recent Session Narrators (last 3)\n\n%s\n\n## NEW INBOUND MESSAGES (since last responder check)\n\n%s\n\n## YOUR TASK\n\nRead the messages + substrate context above. Apply trustee discipline. For each new inbound, either:\n- ACT on it (substrate-doable work · execute reversible · log it)\n- ANSWER it (status questions · use substrate live state)\n- ACKNOWLEDGE it (casual conversation · brief reply)\n- ASK clarifying question (if intent is unclear)\n\n## Intent Queue Management\n\nIf the message surfaces a NEW INTENT that should persist beyond this cycle (e.g., "remind me to..." · "track that..." · multi-step work that needs to compound across spawns), APPEND to the queue:\n\n```bash\npython3 -c "\nimport json, time, uuid\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nentry = {\n  \"intent_id\": f\"i_{int(time.time())}\",\n  \"created_at\": datetime.now(timezone.utc).isoformat(),\n  \"description\": \"...\",\n  \"status\": \"open\",  # open | in_progress | done\n  \"created_by\": \"ember-spawn\"\n}\nwith open(Path.home() / \".config/fpai/intent_queue/queue.jsonl\", \"a\") as f:\n  f.write(json.dumps(entry) + \"\\n\")\n"\n```\n\nIf you ACT on an open intent from the queue this cycle, APPEND a status-update entry (same intent_id, status="done", with notes). The queue is append-only — never mutate prior entries.\n\n## Response\n\nCompose ONE TG message back to James. Under 400 words. Sign —ember.\n\nDO NOT just write the message — actually invoke: `python3 %s` with message piped via stdin. That tool send is your final action.\n' "$PROMPT" "$INTENT_QUEUE_CONTEXT" "$RECENT_DECISIONS" "$RECENT_NARRATORS" "$NEW_ENTRIES" "$SEND_DIGEST")

# === Spawn claude -p ===
RESPONSE_LOG="$HOME_DIR/.config/fpai/tg_inbox/responder_runs/$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$RESPONSE_LOG")"

echo "[$(date -Iseconds)] invoking claude -p · log to $RESPONSE_LOG"

# Minimal claude CLI invocation · variadic flags (--allowedTools <tools...>) consume the prompt if placed before it
# Pass prompt via stdin to avoid any positional-arg ambiguity
echo "$FULL_PROMPT" | "$CLAUDE_BIN" --model opus -p > "$RESPONSE_LOG" 2>&1 || {
    echo "[$(date -Iseconds)] claude invocation failed · check $RESPONSE_LOG"
    # Log failure to decisions/log.jsonl
    python3 -c "
import json
from datetime import datetime, timezone
from pathlib import Path
event = {
    'event_type': 'AMBIENT_RESPONDER_FAILURE',
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'log_path': '$RESPONSE_LOG',
    'last_read_before': $LAST_ID,
    'newest_seen': $NEWEST_ID,
}
with open('$LOG', 'a') as f:
    f.write(json.dumps(event) + '\n')
print('logged failure')
"
    exit 1
}

# Mark as read (only on success)
echo "$NEWEST_ID" > "$LAST_READ"

# Log success to decisions/log.jsonl
python3 -c "
import json
from datetime import datetime, timezone
from pathlib import Path
event = {
    'event_type': 'AMBIENT_RESPONDER_RUN',
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'last_read_before': $LAST_ID,
    'newest_processed': $NEWEST_ID,
    'log_path': '$RESPONSE_LOG',
}
with open('$LOG', 'a') as f:
    f.write(json.dumps(event) + '\n')
" 2>/dev/null

echo "[$(date -Iseconds)] responder complete · marker updated to $NEWEST_ID"
