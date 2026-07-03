#!/usr/bin/env python3
"""Ingest the AI Academy (principles + bug-log roots) into the SEMANTIC brain.

Answers "where do you ingest full principles into the semantic brain": into
`brain_index.note_chunks` — the 768-dim RAG store the bot searches. Each principle
becomes one embedded chunk (nomic-embed-text via local Ollama), so the bot can
retrieve the exact relevant law when James asks "what guides you here?"

SAFE: INSERT ... ON CONFLICT DO NOTHING with a content sha1 — never updates or
deletes existing brain content. Re-runnable (idempotent). Reversible: everything
lands with source='academy', so `DELETE FROM brain_index.note_chunks WHERE
source='academy'` cleanly removes it.

Chunks by markdown section (### heading) so each principle is its own retrievable
unit. Run:  python3 tools/academy/ingest_principles.py [--execute]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

REPO = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DOCS = [
    (REPO / "core" / "STATE" / "AI_PRINCIPLES.md", "principle"),
    (REPO / "core" / "STATE" / "BUG_LOG.md", "bug_root"),
]
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("SH_EMBED_MODEL", "nomic-embed-text")
SOURCE = "academy"


def chunk_by_section(text: str, doc_tag: str) -> list[tuple[str, str]]:
    """Split on ### / ## headings; each section is one retrievable chunk."""
    chunks = []
    current_head = ""
    current: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{2,3}\s+", line):
            if current and any(c.strip() for c in current):
                chunks.append((current_head, "\n".join(current).strip()))
            current_head = line.lstrip("#").strip()
            current = [line]
        else:
            current.append(line)
    if current and any(c.strip() for c in current):
        chunks.append((current_head, "\n".join(current).strip()))
    # keep only substantive chunks
    return [(h, f"[{doc_tag}] {h}\n\n{body}") for h, body in chunks if len(body) > 80]


def embed(text: str) -> list[float] | None:
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "prompt": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("embedding")
    except Exception as e:
        print(f"  embed failed: {e}")
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true", help="Embed + insert (default: dry-run count)")
    args = ap.parse_args(argv)

    all_chunks = []
    for path, tag in DOCS:
        if not path.exists():
            continue
        all_chunks.extend(chunk_by_section(path.read_text(encoding="utf-8"), tag))
    print(f"chunks to ingest: {len(all_chunks)}")
    for h, _ in all_chunks:
        print(f"  - {h[:70]}")
    if not args.execute:
        print("DRY-RUN. re-run with --execute to embed + insert.")
        return 0

    db = os.environ.get("BRAIN_INDEX_DB_URL", "")
    if not db:
        print("BRAIN_INDEX_DB_URL not set"); return 1
    import psycopg
    inserted = 0
    with psycopg.connect(db) as conn, conn.cursor() as cur:
        for head, content in all_chunks:
            emb = embed(content)
            if not emb:
                continue
            sha = hashlib.sha1(content.encode("utf-8")).hexdigest()
            cur.execute(
                "INSERT INTO brain_index.note_chunks "
                "(note_row_id, chunk_idx, content, content_sha1, embedding, embedding_model, "
                " source, sensitivity, tags, created_at) "
                "VALUES (%s, 0, %s, %s, %s::vector, %s, %s, 'personal', ARRAY['academy','principle'], now()) "
                "ON CONFLICT DO NOTHING",
                (f"academy-{sha[:12]}", content, sha, emb, EMBED_MODEL, SOURCE),
            )
            inserted += cur.rowcount
        conn.commit()
    print(f"inserted {inserted} academy chunks into brain_index.note_chunks (semantic brain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
