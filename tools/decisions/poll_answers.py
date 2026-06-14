#!/usr/bin/env python3
"""poll_answers — read James's recent Telegram replies, record decision answers,
and advance the one-chat decision queue. Runs on a cadence (laptop LaunchAgent).

James replies in Telegram with:  <id>: <answer>   (e.g. "d001: safe default")
This finds those, records them via decisions.py (which surfaces the NEXT one),
and dedupes so each answer is recorded once.
"""
import json, os, re, subprocess

HOME = os.path.expanduser("~")
BRIDGE = os.path.join(HOME, "FPAI_Cockpit/tools/memory/tg_brain_bridge.sh")
CONV = os.path.join(HOME, ".config/fpai/tg_brain_bridge/conversation.jsonl")
DEC = os.path.join(HOME, "FPAI_Cockpit/tools/decisions/decisions.py")
SEEN = os.path.join(HOME, ".config/fpai/decisions/seen_answers.txt")

# Refresh the bridge — pull James's latest Telegram messages from server 162.
try:
    subprocess.run(["bash", BRIDGE], timeout=45, capture_output=True)
except Exception:
    pass

seen = set(open(SEEN).read().split("\n")) if os.path.exists(SEEN) else set()
new = []
if os.path.exists(CONV):
    for line in open(CONV, errors="replace"):
        try:
            m = json.loads(line)
        except Exception:
            continue
        if m.get("role") != "james":
            continue
        match = re.search(r"\b(d\d{3})\s*[:\-]\s*(.+)", m.get("text", ""), re.I)
        if not match:
            continue
        did = match.group(1).lower()
        ans = match.group(2).strip()
        key = did + "|" + ans[:40]
        if key in seen:
            continue
        subprocess.run(["python3", DEC, "record", did, ans], timeout=30)
        new.append(key)
        print(f"recorded {did}: {ans[:50]}")

if new:
    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    with open(SEEN, "a") as f:
        f.write("\n".join(new) + "\n")
else:
    print("no new decision answers")
