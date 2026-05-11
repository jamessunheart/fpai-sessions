#!/usr/bin/env python3
"""
Ingest Sunheart legal corpus into sunheart-brain with scope='public', tags=['legal', <source-tag>].

Usage:
  python3 ingest_corpus.py <path> [<path> ...]

Each path can be a PDF, .md, .txt, or directory.

Reads BRAIN_INGEST_TOKEN and BRAIN_INGEST_URL from env.
Strips empty pages, chunks via the index service's own embed/upsert pipeline.
"""
from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path

import httpx

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # only needed for PDFs

BRAIN_INGEST_URL = os.environ.get("BRAIN_INGEST_URL", "https://brain.sunheart.com/ingest")
BRAIN_INGEST_TOKEN = os.environ["BRAIN_INGEST_TOKEN"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest-corpus")


def read_pdf(path: Path) -> str:
    if PdfReader is None:
        raise SystemExit("pypdf not installed: pip install pypdf")
    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def file_to_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return read_pdf(path)
    if ext in (".md", ".txt"):
        return read_text(path)
    raise ValueError(f"Unsupported file type: {ext}")


def source_tag_from_path(path: Path) -> str:
    """Derive a stable tag from the filename."""
    stem = path.stem.lower()
    for old, new in [
        ("180pgchurch_legal_resource", "180pg-church-legal"),
        ("18pgchurch_legal_summary-resource.md", "18pg-church-summary"),
        ("remarkably-coherent-treasury-v0.10", "coherent-treasury-v010"),
        ("legal_framework_synthesis_v2", "legal-framework-synthesis"),
        ("cora nation manifesto", "cora-manifesto"),
        ("cora nation declaration", "cora-declaration"),
        ("cora nation declaration 2", "cora-declaration-2"),
        ("weisss-trustee-handbook", "weisss-trustee-handbook"),
        ("church stewardship declaration june 2025", "church-stewardship-jun2025"),
    ]:
        if old in stem:
            return new
    return stem.replace(" ", "-").replace("_", "-")[:60]


def ingest_doc(path: Path) -> None:
    text = file_to_text(path)
    if not text.strip():
        log.warning(f"empty text from {path}, skipping")
        return
    tag = source_tag_from_path(path)
    body = {
        "title": path.stem,
        "content": text,
        "note_type": "Reference",
        "source": "Manual",
        "source_url": str(path.resolve()),
        "tags": ["legal", tag],
        "sensitivity": "public",
    }
    log.info(f"ingesting {path.name} chars={len(text)} tag={tag}")
    resp = httpx.post(
        BRAIN_INGEST_URL,
        json=body,
        headers={"Authorization": f"Bearer {BRAIN_INGEST_TOKEN}"},
        timeout=120.0,
    )
    if resp.status_code >= 300:
        log.error(f"  failed: {resp.status_code} {resp.text[:200]}")
        return
    log.info(f"  ok: {resp.json().get('row_id', 'no-row-id')}")


def expand_paths(args: list[str]) -> list[Path]:
    out: list[Path] = []
    for a in args:
        p = Path(a).expanduser()
        if p.is_dir():
            out.extend(sorted(p.glob("*.pdf")))
            out.extend(sorted(p.glob("*.md")))
            out.extend(sorted(p.glob("*.txt")))
        elif p.exists():
            out.append(p)
        else:
            log.warning(f"path not found: {a}")
    return out


def main():
    if len(sys.argv) < 2:
        print("usage: ingest_corpus.py <path> [<path> ...]", file=sys.stderr)
        sys.exit(2)
    paths = expand_paths(sys.argv[1:])
    log.info(f"ingesting {len(paths)} files")
    for p in paths:
        try:
            ingest_doc(p)
            time.sleep(0.5)
        except Exception as e:
            log.exception(f"  error on {p}: {e}")


if __name__ == "__main__":
    main()
