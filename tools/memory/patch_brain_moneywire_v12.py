import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# E1 — refresh helper that reads liquid_assets, with a sanity guard
HELPER = '''async def _refresh_treasury_memory() -> None:
    """Regenerate the current-state treasury memory from the live /money ledger so
    conversational answers reflect updates. Sanity-guarded so an empty/garbage
    ledger never clobbers a good current-state seed."""
    try:
        ledger = _money_load_ledger()
        liq = ledger.get("liquid_assets") or {}
        accts = []
        for g in liq.get("groups", []):
            for a in g.get("accounts", []):
                b = float(a.get("balance_usd") or 0)
                if b and not a.get("pending"):
                    accts.append((a.get("name", "?"), b))
        total = sum(b for _, b in accts)
        if total < 50000:
            return
        accts.sort(key=lambda x: -x[1])
        from datetime import datetime as _dt
        head = "about $%dk liquid: " % round(total / 1000)
        head += ", ".join("%s $%.1fk" % (n, b / 1000) for n, b in accts[:8]) + "."
        mem = ("CURRENT STATE as of %s (from the live money ledger, as_of %s) — authoritative, "
               "supersedes older figures.\\nTreasury: %s James's focus: daily income above daily "
               "expenses (~$18k/mo burn); Camp Zen Tier 1 is the fastest income lever."
               % (_dt.now().strftime("%B %d, %Y"), liq.get("as_of", "?"), head))
        emb = await _embed_query(mem)
        if not emb:
            return
        import hashlib as _h
        sha = _h.sha1(mem.encode()).hexdigest()
        from .db import connect
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM brain_index.note_chunks WHERE 'current-state' = ANY(tags)")
                await cur.execute(
                    "INSERT INTO brain_index.note_chunks (note_row_id, chunk_idx, content, content_sha1, "
                    "embedding, embedding_model, source, sensitivity, tags, created_at) "
                    "VALUES (%s,0,%s,%s,%s::vector,%s,'tg-memory','personal',"
                    "ARRAY['tg-memory','current-state'],now())",
                    ("tgmem-current-" + sha[:12], mem, sha, emb, "nomic-embed-text"))
        log.info("treasury memory refreshed from ledger (total=%.0f)", total)
    except Exception as e:
        log.warning("treasury memory refresh failed: %s", e)


def _money_save_ledger(data: dict) -> None:'''
edits.append(("def _money_save_ledger(data: dict) -> None:", HELPER))

# E2 — fire the refresh after every ledger save (any /money update)
edits.append((
    "    _os.replace(tmp, _LEDGER_PATH)\n\n\ndef _money_audit(action: str, payload: dict) -> None:",
    "    _os.replace(tmp, _LEDGER_PATH)\n"
    "    try:\n"
    "        import asyncio as _a\n"
    "        _a.get_running_loop().create_task(_refresh_treasury_memory())\n"
    "    except Exception:\n"
    "        pass\n\n\ndef _money_audit(action: str, payload: dict) -> None:",
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor {n}x: {a[:50]!r}"); sys.exit(1)
    src = src.replace(a, b)
bak = P + ".bak-moneywire-v12-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak); open(P,"w",encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True); print(f"OK applied. bak={bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak,P); print(f"REVERTED: {e}"); sys.exit(1)
