#!/usr/bin/env bash
# TG Brain Bridge — pull the @sunheartbrain_bot conversation off server 162
# into durable local memory, so terminal-Ember can see James's Telegram chats
# and the conversation stops vanishing with journal rotation.
#
# Root cause (2026-06-13): sh-brain-tgbot (curator, on 162) replies via Claude
# API but persists NO conversation log — only the systemd journal, which
# rotates. James caught the bot confabulating ("do you have reference, or did
# you make it up?") because it has no durable memory. This bridge gives both
# terminal-Ember AND a future durable-memory fix a real conversation record.
#
# Pragmatic v0: scrape the journal incrementally. The robust v1 (make the bot
# write its own jsonl) needs server-code authorization — see NEXT in handoff.
set -u
HOST="${TG_BRIDGE_HOST:-root@162.0.208.88}"
OUT="$HOME/.config/fpai/tg_brain_bridge/conversation.jsonl"
SINCE="${1:-2026-06-13 00:00}"   # default: today; pass a date to backfill

LINES=$(ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" \
  "journalctl -u sh-brain-tgbot --since '$SINCE' --no-pager 2>/dev/null \
   | grep -E 'curator\.tgbot (chat|reply|sent):' \
   | sed -E 's/^([A-Za-z]+ [0-9]+ [0-9:]+).*curator\.tgbot /\1\t/'" 2>/dev/null)

[ -z "$LINES" ] && { echo "no new conversation lines since $SINCE"; exit 0; }

# Append as jsonl (ts + role + text), dedup against existing.
python3 - "$OUT" <<PY
import sys, json, os, re
out = sys.argv[1]
seen = set()
if os.path.exists(out):
    for l in open(out):
        try: seen.add(json.loads(l)["raw"])
        except: pass
new = 0
with open(out, "a") as f:
    for line in '''$LINES'''.splitlines():
        if not line.strip() or line in seen: continue
        ts, _, body = line.partition("\t")
        role = "james" if body.startswith("chat:") else "ember"
        text = re.sub(r"^(chat|reply|sent):\s*", "", body)
        f.write(json.dumps({"ts": ts.strip(), "role": role, "text": text.strip(), "raw": line}) + "\n")
        new += 1
print(f"bridged {new} new lines -> {out}")
PY
