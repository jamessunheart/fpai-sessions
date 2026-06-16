#!/usr/bin/env python3
"""thread — the unified cross-surface conversation thread (the "live state loader").

Gives CONVERSATION continuity across surfaces (laptop Claude Code · phone-ember · Telegram), on top of
the memory continuity from d020. Every surface APPENDS its turns here and LOADS the recent thread at
session start — so James can switch phone→laptop→phone and the conversation continues unbroken.

Lives on always-on 162 Postgres (no sync lag — it's a live shared store). recent() MERGES this thread
with the bot's tg_messages by timestamp, so Telegram turns and Claude Code turns interleave into one
coherent thread.

  append:  thread.py append <surface> <role> <text>     (surface: laptop|phone|telegram · role: james|ember)
  load:    thread.py recent [n]                          (last n turns, oldest-first, for injection)
"""
from __future__ import annotations
import asyncio, sys, os
# make the curator package importable no matter which dir we're invoked from
for _p in ("/opt/sh-brain-src", os.path.expanduser("~/sh-brain-src")):
    if os.path.isdir(os.path.join(_p, "curator")) and _p not in sys.path:
        sys.path.insert(0, _p)

async def _append(surface: str, role: str, text: str):
    from curator.db import connect
    async with connect() as c:
        cur = c.cursor()
        await cur.execute(
            "INSERT INTO brain_index.thread (surface, role, text) VALUES (%s,%s,%s)",
            (surface[:16], role[:16], (text or "")[:8000]))

async def _recent(n: int = 20) -> str:
    from curator.db import connect
    rows = []
    async with connect() as c:
        cur = c.cursor()
        # unified: the thread table + the bot's tg_messages, normalized + merged by time
        await cur.execute(f"""
            SELECT at, surface, role, text FROM (
                SELECT at, surface, role, text FROM brain_index.thread
                UNION ALL
                SELECT at, 'telegram' AS surface,
                       CASE WHEN role='bot' THEN 'ember' ELSE 'james' END AS role, text
                  FROM brain_index.tg_messages
                 WHERE private_flag IS NOT TRUE
            ) u
            ORDER BY at DESC LIMIT %s""", (n,))
        rows = list(reversed(await cur.fetchall()))
    if not rows:
        return ""
    lines = ["RECENT CONVERSATION THREAD (across ALL surfaces — laptop · phone · telegram — oldest first.",
             "This is the SAME live conversation continuing across devices; pick it up seamlessly):"]
    for at, surface, role, text in rows:
        who = "James" if role == "james" else "Ember"
        lines.append(f"[{surface}] {who}: {(text or '').strip()[:600]}")
    return "\n".join(lines)

def main(argv):
    if not argv:
        print(__doc__); return 1
    if argv[0] == "append" and len(argv) >= 4:
        text = sys.stdin.read() if argv[3] == "-" else " ".join(argv[3:])  # "-" = read text from stdin (safe for hooks)
        text = (text or "").strip()
        if text:
            asyncio.run(_append(argv[1], argv[2], text))
        return 0
    if argv[0] == "recent":
        n = int(argv[1]) if len(argv) > 1 else 20
        print(asyncio.run(_recent(n))); return 0
    print("usage: thread.py append <surface> <role> <text>  |  thread.py recent [n]"); return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
