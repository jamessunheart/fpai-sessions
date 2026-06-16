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
# self-load the DB env so this works from hooks / ssh without a sourced shell
if not os.environ.get("BRAIN_INDEX_DB_URL"):
    for _ef in ("/etc/sh-brain/curator.env",):
        if os.path.isfile(_ef):
            for _ln in open(_ef):
                _ln = _ln.strip()
                if _ln and not _ln.startswith("#") and "=" in _ln:
                    _k, _v = _ln.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

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
        # thread table filtered: exclude system prompts that leaked in via claude -p hook
        await cur.execute(f"""
            SELECT at, surface, role, text FROM (
                SELECT at, surface, role, text FROM brain_index.thread
                 WHERE length(text) <= 600
                   AND text NOT LIKE 'Goal: identify the single highest%%'
                   AND text NOT LIKE 'Branch build/%%'
                   AND text NOT LIKE '[Module blueprints%%'
                   AND text NOT LIKE 'You are an independent%%'
                   AND text NOT LIKE 'DECISION QUEUE:%%'
                   AND text NOT LIKE 'Diff to review:%%'
                   AND NOT (text LIKE '{{%%' AND role = 'james')
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

async def _state() -> str:
    """Compact CURRENT live system-state (so a surface boots with live truth, not just conversation)."""
    import subprocess
    try:
        loop = subprocess.run(["systemctl", "is-active", "fpai-build-loop.timer"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        loop = "unknown"
    bits = [f"build loop {loop} (server 162, laptop-free, $0)"]
    try:
        from curator.db import connect
        async with connect() as c:
            cur = c.cursor()
            await cur.execute("select id,left(question,56) from brain_index.decisions where status='answered' and needs_build=true and coalesce(spec_written,false)=false order by id desc limit 1")
            r = await cur.fetchone(); bits.append(f"queued-next: {r[0]}:{r[1].strip()}" if r else "queued-next: none")
            await cur.execute("select id,left(question,56) from brain_index.decisions where build_status='built' order by id desc limit 1")
            r = await cur.fetchone(); bits.append(f"last-built: {r[0]}:{r[1].strip()}" if r else "last-built: none")
    except Exception:
        pass
    return "CURRENT LIVE SYSTEM STATE (now — report as truth, not the older thread below): " + " · ".join(bits)

def main(argv):
    if not argv:
        print(__doc__); return 1
    if argv[0] == "state":
        print(asyncio.run(_state())); return 0
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
