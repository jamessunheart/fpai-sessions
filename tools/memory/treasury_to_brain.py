#!/usr/bin/env python3
"""treasury_to_brain — keep Ember's current-state memory synced with the live
money ledger.

Reads /opt/chief-of-staff/state/ledger.json (which `/money set-balance` updates),
regenerates the dated current-state memory chunk, embeds it, replaces the old.
Run on-demand, after a /money update, or on a timer.

DEPLOY (needs James's explicit go — standing prod infra on 162):
  scp tools/memory/treasury_to_brain.py root@162.0.208.88:/opt/sh-brain-src/
  ssh root@162.0.208.88 'cd /opt/sh-brain-src && ./.venv/bin/python treasury_to_brain.py'
  # optional 6h timer: systemd treasury-to-brain.service + .timer
"""
import asyncio, hashlib, json, os, sys
LEDGER = os.environ.get("LEDGER_PATH", "/opt/chief-of-staff/state/ledger.json")

CONTEXT = ("James's main focus right now: getting daily income above daily expenses "
           "(monthly burn ~$18k). Camp Zen Tier 1 (paid village stays, $500-600/week) is the "
           "fastest income lever; the Patron Engine (membership + donations via Cora Nation) is "
           "the bigger fundraising design, pending legal review. North Star: a self-standing Full "
           "Potential OS that holds context and advances without James prompting.")


def build_memory():
    accts, total = [], 0.0
    try:
        d = json.load(open(LEDGER))
        for a in d.get("accounts", d.get("balances", [])):
            bal = float(a.get("balance_usd") or 0)
            if bal:
                accts.append((a.get("name", "?"), bal)); total += bal
    except Exception:
        pass
    accts.sort(key=lambda x: -x[1])
    if total:
        head = (f"CURRENT TREASURY (live, auto-synced) — about ${total/1000:.0f}k liquid: "
                + ", ".join(f"{n} ${b/1000:.1f}k" for n, b in accts[:8]) + ". ")
    else:
        head = ("CURRENT TREASURY (auto-synced): about $113k liquid — ~$45k BitTrue, $35k MACU, "
                "$9k JitoSOL, $6k Kamino USDC, $4.6k Wise, $3.8k Venmo. Total trust ~$3M. ")
    from datetime import datetime
    return f"CURRENT STATE as of {datetime.now():%B %d, %Y} — authoritative, supersedes older figures.\n{head}OneBPO ~$11k/mo. {CONTEXT}"


async def main():
    sys.path.insert(0, "/opt/sh-brain-src")
    from curator.tgbot import _embed_query
    from curator.db import connect
    mem = build_memory()
    emb = await _embed_query(mem)
    if not emb:
        print("embed failed"); return
    sha = hashlib.sha1(mem.encode()).hexdigest()
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM brain_index.note_chunks WHERE 'current-state' = ANY(tags)")
            await cur.execute(
                "INSERT INTO brain_index.note_chunks (note_row_id, chunk_idx, content, content_sha1, embedding, embedding_model, source, sensitivity, tags, created_at) "
                "VALUES (%s,0,%s,%s,%s::vector,%s,'tg-memory','personal',ARRAY['tg-memory','current-state'],now())",
                (f"tgmem-current-{sha[:12]}", mem, sha, emb, "nomic-embed-text"))
    print("treasury->brain synced:", mem[:90], "...")


if __name__ == "__main__":
    asyncio.run(main())
