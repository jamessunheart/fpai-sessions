#!/usr/bin/env python3
"""
mirror_pull · v2 · 2026-07-02  ·  SSOT DESIGN §8 — smallest safe build

Pulls a READ-ONLY brain digest into the Obsidian vault, so James can see what
the AI brain holds. Manual command. No background job. No Telegram. No secrets.

  brain server (brain_index DB)
        │  ssh · source env on server · run read-only SELECTs via brain venv
        │  (DB creds stay on the server — only the numbers come back)
        ▼
  vault  02_CONTEXT/Memory/BRAIN DIGEST.md   (semantic RAG brain)
  vault  02_CONTEXT/Memory/BRAIN STATE.md    (operational: decisions · corrections · insights · thread)
  vault  02_CONTEXT/Memory/HOT STATE.md      (HOT_STATE — live synthesized picture from 5 scanners)

Why this shape:
  - Read-only: copies the digest job's SELECTs, NOT its write step.
  - No Telegram: pure SSH/DB read — cannot conflict with the bot's poller.
  - No secrets: env is sourced server-side; only aggregate counts transit.

Usage:
  python3 mirror_pull.py          # pull latest digest into the vault
  python3 mirror_pull.py --print  # print to stdout, do not write the file
"""
from __future__ import annotations

import argparse
import os
import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SERVER = "root@162.0.208.88"
ENV_FILE = "/etc/sh-brain/curator.env"          # sourced ON the server, never read here
VENV_PY = "/opt/sh-brain-src/.venv/bin/python"

# Prefer the local vault path. Older runs preferred the iCloud Obsidian path when
# it existed, but unattended macOS processes can see that path and still hit TCC
# PermissionError on mkdir/write. Keep iCloud as a fallback for machines where it
# is the only vault, but never let an inaccessible iCloud path kill fpull.
_VAULT_ICLOUD = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "Full Potential OS"
_VAULT_DOCS   = HOME / "Documents" / "FPOS" / "Full Potential OS"
_EXPLICIT_VAULT = os.environ.get("FPAI_VAULT")


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    out = []
    seen = set()
    for path in paths:
        key = str(path.expanduser())
        if key not in seen:
            seen.add(key)
            out.append(path.expanduser())
    return out


def vault_candidates() -> list[Path]:
    if _EXPLICIT_VAULT:
        return [Path(_EXPLICIT_VAULT).expanduser()]
    defaults = [_VAULT_DOCS, _VAULT_ICLOUD]
    existing = [path for path in defaults if path.exists()]
    if existing:
        return _dedupe_paths(existing + [_VAULT_DOCS])
    return _dedupe_paths(defaults)


def choose_vault(candidates: list[Path] | None = None) -> Path:
    candidates = candidates or vault_candidates()
    for vault in candidates:
        if vault.exists():
            return vault
    return candidates[0]


VAULT = choose_vault()
DIGEST_FILE = VAULT / "02_CONTEXT/Memory" / "BRAIN DIGEST.md"

# Read-only query, run by the brain's own venv on the server. No writes.
REMOTE_PY = r"""
import os, json, asyncio, psycopg
from datetime import datetime, timezone
from pathlib import Path
DB = os.environ.get("BRAIN_INDEX_DB_URL")
async def main():
    out = {}
    conn = await psycopg.AsyncConnection.connect(DB, autocommit=True)
    async with conn.cursor() as cur:
        # Semantic RAG brain
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.note_chunks"); out['total_chunks']=(await cur.fetchone())[0]
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.concepts"); out['total_concepts']=(await cur.fetchone())[0]
        await cur.execute("SELECT sensitivity, COUNT(*)::int FROM brain_index.note_chunks WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY sensitivity"); out['new_24h_by_sens']=dict(await cur.fetchall())
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.merge_log WHERE at > NOW() - INTERVAL '24 hours'"); out['merges_24h']=(await cur.fetchone())[0]
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.audit_log WHERE at > NOW() - INTERVAL '24 hours' AND blocked=true"); out['blocked_24h']=(await cur.fetchone())[0]
        await cur.execute("SELECT agent, COUNT(*)::int FROM brain_index.audit_log WHERE at > NOW() - INTERVAL '24 hours' GROUP BY agent ORDER BY 2 DESC LIMIT 8"); out['top_agents']=[{'agent':a,'calls':n} for a,n in await cur.fetchall()]
        # Operational brain — decisions
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.decisions WHERE build_status='merged'"); out['merged_specs']=(await cur.fetchone())[0]
        await cur.execute("SELECT id, left(question,70) FROM brain_index.decisions WHERE build_status IN ('built','merged') ORDER BY created_at DESC LIMIT 5"); out['recent_merged']=[{'id':r[0],'q':r[1]} for r in await cur.fetchall()]
        await cur.execute("SELECT id, left(question,70) FROM brain_index.decisions WHERE status='answered' AND build_status NOT IN ('merged','rejected') ORDER BY created_at DESC LIMIT 5"); out['in_pipeline']=[{'id':r[0],'q':r[1]} for r in await cur.fetchall()]
        await cur.execute("SELECT id, left(question,70) FROM brain_index.decisions WHERE status='open' ORDER BY created_at DESC LIMIT 3"); out['awaiting_james']=[{'id':r[0],'q':r[1]} for r in await cur.fetchall()]
        # Corrections (James's taste signals)
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.corrections"); out['correction_count']=(await cur.fetchone())[0]
        await cur.execute("SELECT left(original_response,60), left(james_correction,60) FROM brain_index.corrections ORDER BY created_at DESC LIMIT 3"); out['recent_corrections']=[{'orig':r[0],'fixed':r[1]} for r in await cur.fetchall()]
        # Session insights (7-day active window)
        await cur.execute("SELECT insight_type, title, left(body,100), weight FROM brain_index.session_insights WHERE ts > NOW() - INTERVAL '7 days' AND insight_type != 'housekeeping' AND title NOT LIKE 'Auto-snapshot%%' ORDER BY weight DESC, ts DESC LIMIT 6"); out['active_insights']=[{'type':r[0],'title':r[1],'body':r[2],'w':r[3]} for r in await cur.fetchall()]
        # Thread (conversation continuity)
        await cur.execute("SELECT COUNT(*)::int FROM brain_index.thread"); out['thread_count']=(await cur.fetchone())[0]
        await cur.execute("SELECT surface, left(content,80) FROM brain_index.thread ORDER BY ts DESC LIMIT 3"); out['thread_recent']=[{'src':r[0],'msg':r[1]} for r in await cur.fetchall()]
    await conn.close()
    # HOT_STATE (the live unified picture)
    hot_path = Path(os.environ.get('FPAI_HOT_STATE', '/root/.config/fpai/hot_memory/HOT_STATE.md'))
    out['hot_state'] = hot_path.read_text(errors='ignore')[:4000] if hot_path.exists() else ''
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


def render_build_state(d: dict) -> str:
    ts = d.get("ts", "").replace("T", " ")[:16] + " UTC"

    merged = d.get("merged_specs", 0)
    recent = d.get("recent_merged", [])
    pipeline = d.get("in_pipeline", [])
    awaiting = d.get("awaiting_james", [])
    recent_lines = "\n".join(f"- `{r['id']}` — {r['q']}" for r in recent) or "- (none)"
    pipeline_lines = "\n".join(f"- `{r['id']}` — {r['q']}" for r in pipeline) or "- (none)"
    awaiting_lines = "\n".join(f"- `{r['id']}` — {r['q']}" for r in awaiting) or "- (none)"

    corr_count = d.get("correction_count", 0)
    recent_corr = d.get("recent_corrections", [])
    corr_lines = "\n".join(f"- ~~{r['orig']}~~ → {r['fixed']}" for r in recent_corr) or "- (none)"

    insights = d.get("active_insights", [])
    insight_lines = "\n".join(
        f"- **[w{i['w']}] {i['type']}** — {i['title']}: {i['body']}" for i in insights
    ) or "- (none active this week)"

    thread_count = d.get("thread_count", 0)
    thread_recent = d.get("thread_recent", [])
    thread_lines = "\n".join(f"- `{r['src']}`: {r['msg']}" for r in thread_recent) or "- (none)"

    return (
        "# BRAIN STATE\n\n"
        "*Operational snapshot — decisions, corrections, insights, conversation thread. "
        "Read-only pull from brain_index on server 162. Refresh: `fpull`*\n\n"
        f"**Pulled:** {ts}\n\n"
        "---\n\n"
        "## Build history\n\n"
        f"**{merged} specs merged total.**\n\n"
        f"### Recent merges\n{recent_lines}\n\n"
        f"### In pipeline (built, not merged)\n{pipeline_lines}\n\n"
        f"### Awaiting James answer\n{awaiting_lines}\n\n"
        "---\n\n"
        "## Corrections (James's taste signals)\n\n"
        f"**{corr_count} total corrections recorded.** Last 3:\n\n"
        f"{corr_lines}\n\n"
        "---\n\n"
        "## Session insights (active this week)\n\n"
        f"{insight_lines}\n\n"
        "---\n\n"
        "## Conversation thread\n\n"
        f"**{thread_count} messages across all surfaces** (laptop · phone · Telegram).\n\n"
        f"Most recent:\n{thread_lines}\n\n"
        "---\n\n"
        "*Source: `brain_index` DB on sh-brain · read-only. Refresh: `python3 FPAI_Cockpit/tools/decisions/mirror_pull.py`*\n"
    )


def write_vault_text(rel_path: str, text: str, candidates: list[Path] | None = None) -> Path:
    """Write a vault-relative file, falling back across default vault candidates.

    This specifically handles macOS/iCloud TCC behavior: the iCloud directory can
    exist but deny writes from an unattended process. Explicit FPAI_VAULT remains
    explicit: with only one candidate, its PermissionError is surfaced.
    """
    errors = []
    for vault in candidates or vault_candidates():
        dest = vault / rel_path
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
            return dest
        except PermissionError as exc:
            errors.append(f"{dest}: {exc}")
            continue
    detail = "; ".join(errors) or rel_path
    raise PermissionError(f"could not write vault mirror after trying candidates: {detail}")


# State docs to mirror from repo into vault (read from laptop repo clone, no SSH needed)
LAPTOP_REPO = HOME / "FPAI_Cockpit"
STATE_DOCS = [
    ("core/STATE/SYSTEM_ARCHITECTURE.md", "02_CONTEXT/Memory/SYSTEM ARCHITECTURE.md"),
    ("core/STATE/NOW.md",                 "02_CONTEXT/Memory/NOW — Current Priorities.md"),
    ("core/STATE/AI_GOALS.md",            "02_CONTEXT/Memory/AI GOALS.md"),
]


def mirror_state_docs(vault: Path, repo: Path) -> list[str]:
    """Copy key state docs from the local repo clone into the vault. No SSH."""
    copied = []
    for src_rel, dest_rel in STATE_DOCS:
        src = repo / src_rel
        if not src.exists():
            continue
        dest = vault / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text())
        copied.append(dest.name)
    return copied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="print_only",
                    help="Print to stdout, do not write the vault file")
    ap.add_argument("--repo", type=Path, default=LAPTOP_REPO,
                    help="Path to local FPAI_Cockpit repo clone")
    args = ap.parse_args()

    data = fetch()
    md = render(data)
    md_state = render_build_state(data)

    if args.print_only:
        print(md)
        print("\n\n" + "=" * 60 + "\n")
        print(md_state)
        hot = data.get("hot_state", "")
        if hot:
            print("\n\n" + "=" * 60 + "\n")
            print(hot)
        return 0

    candidates = vault_candidates()
    digest_file = write_vault_text("02_CONTEXT/Memory/BRAIN DIGEST.md", md, candidates)
    vault = digest_file.parents[1]
    print(f"wrote {digest_file.name}  ·  {data.get('total_chunks', 0):,} chunks")

    state_file = write_vault_text("02_CONTEXT/Memory/BRAIN STATE.md", md_state, candidates)
    print(f"wrote {state_file.name}  ·  {data.get('merged_specs', 0)} specs merged")

    hot = data.get("hot_state", "")
    if hot:
        hot_file = write_vault_text("02_CONTEXT/Memory/HOT STATE.md", hot, candidates)
        print(f"wrote {hot_file.name}")

    # Also mirror key state docs from local repo clone
    copied = mirror_state_docs(vault, args.repo)
    if copied:
        print(f"mirrored: {', '.join(copied)}")
    else:
        print(f"(state docs not found — expected repo at {args.repo})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
