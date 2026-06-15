#!/usr/bin/env python3
"""Bridge: read the LIVE brain_index.corrections table -> append d010 preference pairs to the dataset.

This closes the L2 gate (James greenlit 2026-06-15): curator/corrections.py captures James's
corrections into Postgres on the live bot; this bridge converts each row into the SAME preference-pair
shape tools/learn/capture_corrections.py already produces, and appends (deduped) to the training JSONL
that the reward-LoRA will consume. Reuses make_correction_pair + append_pair — no duplicate logic.

CAPTURE/PREP ONLY: reads + writes a local JSONL. Does not train, deploy, route, or grant authority.
Run under a venv that has psycopg (e.g. the bot venv) with BRAIN_INDEX_DB_URL in env:
    set -a; . /etc/sh-brain/curator.env; set +a
    /opt/sh-brain-src/.venv/bin/python tools/learn/sync_corrections_to_dataset.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# import the already-tested pair builder from the sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_corrections import make_correction_pair, append_pair, DEFAULT_DATASET  # noqa: E402


def _dsn() -> str | None:
    for k in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        v = os.environ.get(k)
        if v:
            return v
    return None


def fetch_corrections(limit: int = 5000) -> list[dict]:
    """Read correction rows from the live table. Returns [] if psycopg/DSN unavailable (safe degrade)."""
    dsn = _dsn()
    if not dsn:
        print("no DSN in env (BRAIN_INDEX_DB_URL) — nothing to sync", file=sys.stderr)
        return []
    try:
        import psycopg
    except ImportError:
        print("psycopg not available in this interpreter — run under the bot venv", file=sys.stderr)
        return []
    rows: list[dict] = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT conversation_id, bot_turn_id, original_response, james_correction, "
                "captured_at::text FROM brain_index.corrections ORDER BY captured_at ASC LIMIT %s",
                (limit,),
            )
            for cid, bot_turn_id, original, correction, captured_at in cur.fetchall():
                rows.append({
                    "conversation_id": cid,
                    "bot_turn_id": bot_turn_id,
                    "original_response": original or "",
                    "james_correction": correction or "",
                    "captured_at": captured_at,
                })
    return rows


def sync(*, dataset: Path | str = DEFAULT_DATASET, dry_run: bool = False) -> dict:
    rows = fetch_corrections()
    added = skipped = 0
    for r in rows:
        if not r["original_response"].strip() or not r["james_correction"].strip():
            continue
        pair = make_correction_pair(
            rejected=r["original_response"],
            preferred=r["james_correction"],
            prompt="",
            source="brain_index.corrections",
            metadata={"conversation_id": r["conversation_id"], "bot_turn_id": r["bot_turn_id"]},
            captured_at=r["captured_at"],
        )
        if dry_run:
            added += 1
            continue
        if append_pair(pair, dataset, dedupe=True):
            added += 1
        else:
            skipped += 1
    return {"read": len(rows), "added": added, "skipped_dupes": skipped, "dataset": str(dataset), "dry_run": dry_run}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sync live brain_index.corrections -> preference dataset.")
    p.add_argument("--dry-run", action="store_true", help="Count without writing")
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = p.parse_args(argv)
    import json
    print(json.dumps(sync(dataset=args.dataset, dry_run=args.dry_run), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
