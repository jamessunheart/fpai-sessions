#!/usr/bin/env python3
"""
mirror_pull · v1 · 2026-05-31  ·  SSOT DESIGN §8 — smallest safe build

Pulls a READ-ONLY brain digest into the Obsidian vault, so James can see what
the AI brain holds. Manual command. No background job. No Telegram. No secrets.

  brain server (brain_index DB)
        │  ssh · source env on server · run read-only SELECTs via brain venv
        │  (DB creds stay on the server — only the numbers come back)
        ▼
  vault  00_MEMORY/BRAIN DIGEST.md   (latest snapshot, overwritten each run)

Why this shape:
  - Read-only: copies the digest job's SELECTs, NOT its write step.
  - No Telegram: pure SSH/DB read — cannot conflict with the bot's poller.
  - No secrets: env is sourced server-side; only aggregate counts transit.

Usage:
  python3 mirror_pull.py          # pull latest digest into the vault
  python3 mirror_pull.py --print  # print to stdout, do not write the file
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SERVER = "root@162.0.208.88"
ENV_FILE = "/etc/sh-brain/curator.env"          # sourced ON the server, never read here
VENV_PY = "/opt/sh-brain-src/.venv/bin/python"

VAULT = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
DIGEST_FILE = VAULT / "00_MEMORY" / "BRAIN DIGEST.md"

# Read-only query, run by the brain's own venv on the server. No writes.
REMOTE_PY = r"""
import os, json, asyncio, psycopg
from datetime import datetime, timezone
DB = os.environ.get("BRAIN_INDEX_DB_URL")
async def main():
    out = {}
    conn = await psycopg.AsyncConnection.connect(DB, autocommit=True)
    async with conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.note_chunks"); out['total_chunks']=(await cur.fetchone())[0]
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.concepts"); out['total_concepts']=(await cur.fetchone())[0]
        await cur.execute("SELECT sensitivity, COUNT(*)::int FROM brain_index.note_chunks WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY sensitivity"); out['new_24h_by_sens']=dict(await cur.fetchall())
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.merge_log WHERE at > NOW() - INTERVAL '24 hours'"); out['merges_24h']=(await cur.fetchone())[0]
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.audit_log WHERE at > NOW() - INTERVAL '24 hours' AND blocked=true"); out['blocked_24h']=(await cur.fetchone())[0]
        await cur.execute("SELECT agent, COUNT(*)::int FROM brain_index.audit_log WHERE at > NOW() - INTERVAL '24 hours' GROUP BY agent ORDER BY 2 DESC LIMIT 8"); out['top_agents']=[{'agent':a,'calls':n} for a,n in await cur.fetchall()]
    await conn.close()
    out['ts']=datetime.now(timezone.utc).isoformat()
    print(json.dumps(out))
asyncio.run(main())
"""

REMOTE_CMD = f"set -a; . {ENV_FILE} 2>/dev/null; set +a; {VENV_PY} -"


def fetch() -> dict:
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", SERVER, REMOTE_CMD],
        input=REMOTE_PY, capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        print(f"ssh/query failed: {r.stderr.strip()[:300]}", file=sys.stderr)
        sys.exit(1)
    # Last non-empty line is the JSON payload (ignore any benign warnings above it).
    for line in reversed(r.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    print(f"no JSON in response: {r.stdout[:300]}", file=sys.stderr)
    sys.exit(1)


def render(d: dict) -> str:
    ts = d.get("ts", "").replace("T", " ")[:16] + " UTC"
    by_sens = d.get("new_24h_by_sens", {})
    new_total = sum(by_sens.values())
    sens_str = ", ".join(f"{k}: {v}" for k, v in by_sens.items()) or "—"
    agents = d.get("top_agents", [])
    agent_lines = "\n".join(f"- {a['agent']} — {a['calls']} calls" for a in agents) or "- (none in 24h)"

    return (
        "# BRAIN DIGEST\n\n"
        "*Read-only snapshot of what the AI brain holds. Pulled manually — "
        "this reflects the last pull, not live. Run again to refresh.*\n\n"
        f"**Pulled:** {ts}\n\n"
        "---\n\n"
        "## Totals\n\n"
        f"- Memories (chunks): **{d.get('total_chunks', 0):,}**\n"
        f"- Concepts: **{d.get('total_concepts', 0):,}**\n\n"
        "## Last 24 hours\n\n"
        f"- New memories: **{new_total}**  ({sens_str})\n"
        f"- Auto-merges: {d.get('merges_24h', 0)}\n"
        f"- Blocked queries: {d.get('blocked_24h', 0)}\n\n"
        "## Most active agents (24h)\n\n"
        f"{agent_lines}\n\n"
        "---\n\n"
        "*Source: `brain_index` DB on sh-brain · read-only · no secrets stored. "
        "Refresh: `python3 FPAI_Cockpit/tools/decisions/mirror_pull.py`*\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="print_only",
                    help="Print to stdout, do not write the vault file")
    args = ap.parse_args()

    data = fetch()
    md = render(data)

    if args.print_only:
        print(md)
        return 0

    DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_FILE.write_text(md)
    print(f"wrote {DIGEST_FILE.name}  ·  {data.get('total_chunks', 0):,} chunks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
