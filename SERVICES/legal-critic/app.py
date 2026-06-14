"""
legal-critic — The Counsel
A specialized AI critic grounded in the Sunheart legal corpus (180pg Church Legal,
Coherent Treasury v0.10, CORA Nation declarations, trustee handbook, etc.).

Self-contained: owns its own corpus + vector store. No dependency on sh-brain-index.
Cross-tool access via HTTP API (any AI / CLI / future tool POSTs to /critique).

Endpoints:
- POST /critique  — submit a doc, get a structured legal critique
- POST /search    — retrieve relevant corpus chunks for a query
- POST /reindex   — rebuild corpus index (admin)
- GET  /healthz   — liveness + corpus status
- GET  /sources   — list corpus source files + chunk counts

Auth: shared FPAI bearer token (Authorization: Bearer <token>).
"""
from __future__ import annotations

import os
import json
import time
import pickle
import logging
import threading
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("legal-critic")

CORPUS_DIR = Path(os.environ.get("CORPUS_DIR", "/opt/legal-critic/corpus"))
INDEX_PATH = Path(os.environ.get("INDEX_PATH", "/opt/legal-critic/corpus/.index.pkl"))
SYSTEM_PROMPT_PATH = Path(os.environ.get(
    "SYSTEM_PROMPT_PATH", "/opt/legal-critic/system-prompts/legal_critic.md"
))
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
LEGAL_CRITIC_TOKENS = json.loads(os.environ.get("LEGAL_CRITIC_TOKENS", "{}"))

CHUNK_CHARS = 1800
CHUNK_OVERLAP = 200

claude = Anthropic(api_key=ANTHROPIC_API_KEY)
security = HTTPBearer()
app = FastAPI(title="legal-critic", version="0.1.0")

_INDEX_LOCK = threading.Lock()
_INDEX: dict = {"chunks": [], "embeddings": None, "built_at": None}


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────


def _authenticate(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not creds or not creds.credentials:
        raise HTTPException(401, "missing bearer token")
    agent = LEGAL_CRITIC_TOKENS.get(creds.credentials)
    if not agent:
        raise HTTPException(401, "invalid token")
    return agent


# ──────────────────────────────────────────────────────────────────────────────
# Corpus loading + chunking + embedding
# ──────────────────────────────────────────────────────────────────────────────


def _read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _chunk(text: str, source: str) -> list[dict]:
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + CHUNK_CHARS, n)
        content = text[i:end].strip()
        if len(content) > 100:
            chunks.append({"source": source, "content": content, "start": i, "end": end})
        i = end - CHUNK_OVERLAP if end < n else n
    return chunks


def _embed_batch(texts: list[str]) -> np.ndarray:
    """OpenAI embeddings. Batches of up to 100."""
    out: list[list[float]] = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i + 100]
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            json={"model": EMBED_MODEL, "input": batch},
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        out.extend(d["embedding"] for d in data)
    return np.array(out, dtype=np.float32)


def _build_index() -> dict:
    log.info(f"building index from {CORPUS_DIR}")
    chunks: list[dict] = []
    for path in sorted(CORPUS_DIR.glob("**/*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in (".pdf", ".md", ".txt"):
            continue
        try:
            text = _read_file(path)
            if not text.strip():
                log.warning(f"  empty: {path}")
                continue
            file_chunks = _chunk(text, source=path.name)
            log.info(f"  {path.name}: {len(file_chunks)} chunks")
            chunks.extend(file_chunks)
        except Exception as e:
            log.exception(f"  error reading {path}: {e}")

    if not chunks:
        return {"chunks": [], "embeddings": None, "built_at": time.time()}

    log.info(f"embedding {len(chunks)} chunks with {EMBED_MODEL}")
    embeddings = _embed_batch([c["content"] for c in chunks])
    # L2-normalize for cosine via dot product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms

    index = {
        "chunks": chunks,
        "embeddings": embeddings,
        "built_at": time.time(),
        "embed_model": EMBED_MODEL,
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open("wb") as f:
        pickle.dump(index, f)
    log.info(f"index saved: {INDEX_PATH}")
    return index


def _load_or_build_index() -> dict:
    if INDEX_PATH.exists():
        try:
            with INDEX_PATH.open("rb") as f:
                idx = pickle.load(f)
            log.info(f"loaded index: {len(idx['chunks'])} chunks, built {time.ctime(idx['built_at'])}")
            return idx
        except Exception as e:
            log.warning(f"failed to load cached index ({e}); rebuilding")
    return _build_index()


def _retrieve(query: str, k: int = 8) -> list[dict]:
    with _INDEX_LOCK:
        idx = _INDEX
        if idx["embeddings"] is None or len(idx["chunks"]) == 0:
            return []
        q_emb = _embed_batch([query])[0]
        q_emb = q_emb / (np.linalg.norm(q_emb) + 1e-9)
        scores = idx["embeddings"] @ q_emb  # cosine since normalized
        top_idx = np.argsort(-scores)[:k]
        return [
            {**idx["chunks"][i], "score": float(scores[i])}
            for i in top_idx
        ]


# ──────────────────────────────────────────────────────────────────────────────
# API models
# ──────────────────────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str
    k: int = 8


class SearchHit(BaseModel):
    score: float
    content: str
    source: str


class CritiqueRequest(BaseModel):
    doc_text: str = Field(..., description="The document to critique (markdown or plain text).")
    focus: Optional[str] = Field(
        None,
        description="Optional focus: 'securities', 'tax', 'CORA structure', 'PMA', 'AML', 'trust law', etc.",
    )
    k: int = Field(8, description="Number of legal corpus chunks to retrieve.")
    model: Optional[str] = Field(None, description="Override Anthropic model.")


class CritiqueResponse(BaseModel):
    critique_md: str
    model: str
    retrieved_chunks: int
    sources_used: list[str]
    elapsed_ms: int


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────


@app.on_event("startup")
def _startup():
    global _INDEX
    _INDEX = _load_or_build_index()


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "model": ANTHROPIC_MODEL,
        "chunks": len(_INDEX.get("chunks", [])),
        "built_at": _INDEX.get("built_at"),
    }


@app.get("/sources")
def sources(agent: str = Depends(_authenticate)):
    counts: dict[str, int] = {}
    for c in _INDEX.get("chunks", []):
        counts[c["source"]] = counts.get(c["source"], 0) + 1
    return {"sources": counts, "total_chunks": sum(counts.values())}


@app.post("/reindex")
def reindex(agent: str = Depends(_authenticate)):
    global _INDEX
    with _INDEX_LOCK:
        _INDEX = _build_index()
    return {"ok": True, "chunks": len(_INDEX["chunks"])}


@app.post("/search", response_model=list[SearchHit])
def search(req: SearchRequest, agent: str = Depends(_authenticate)):
    hits = _retrieve(req.query, k=req.k)
    return [SearchHit(score=h["score"], content=h["content"], source=h["source"]) for h in hits]


@app.post("/critique", response_model=CritiqueResponse)
def critique(req: CritiqueRequest, agent: str = Depends(_authenticate)):
    t0 = time.time()
    model = req.model or ANTHROPIC_MODEL

    retrieval_query = (req.focus + "\n\n" if req.focus else "") + req.doc_text[:1500]
    hits = _retrieve(retrieval_query, k=req.k)
    corpus_text = "\n\n".join(
        f"--- CORPUS CHUNK {i} (source: {h['source']}, score: {h['score']:.3f}) ---\n{h['content']}"
        for i, h in enumerate(hits, 1)
    )

    system_prompt = SYSTEM_PROMPT_PATH.read_text()
    today = time.strftime("%Y-%m-%d")
    user_content = (
        f"Today's date: {today}.\n\n"
        "# DOC UNDER REVIEW\n\n"
        f"{req.doc_text}\n\n"
        "---\n\n"
        "# RELEVANT LEGAL CORPUS (retrieved from Sunheart legal knowledge base)\n\n"
        f"{corpus_text}\n\n"
        "---\n\n"
        "# YOUR TASK\n\n"
        "Critique the doc under review using the legal corpus as your grounded knowledge base. "
        "Follow the output format in your system prompt strictly. "
        f"Set 'Reviewed:' to {today}.\n"
        + (f"\nFocus area: {req.focus}\n" if req.focus else "")
    )

    log.info(
        f"critique agent={agent} doc_chars={len(req.doc_text)} retrieved={len(hits)} model={model}"
    )

    msg = claude.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    critique_md = "".join(
        block.text for block in msg.content if getattr(block, "type", None) == "text"
    )

    sources_used = sorted({h["source"] for h in hits})
    elapsed_ms = int((time.time() - t0) * 1000)
    return CritiqueResponse(
        critique_md=critique_md,
        model=model,
        retrieved_chunks=len(hits),
        sources_used=sources_used,
        elapsed_ms=elapsed_ms,
    )
