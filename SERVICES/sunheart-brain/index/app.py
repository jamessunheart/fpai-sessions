"""
brain-index — the semantic index for Sunheart Brain.

Wraps pgvector behind a small FastAPI surface. Two audiences:

1. Internal:  sh-mcp-http and brain-ingest call us directly on localhost.
2. External:  GPT Custom Connector / Custom GPT Actions import our OpenAPI
              spec at /openapi.json and call us over HTTPS with a bearer token.

Embedding routing:
    - default:   local Ollama (nomic-embed-text, 768-dim, free)
    - opt-in:    OpenAI text-embedding-3-small (1536-dim, paid)
    `prefer=openai` on any embedding request forces OpenAI if OPENAI_API_KEY
    is set; otherwise silently falls back to local.

Config (env):
    BRAIN_INDEX_DB_URL         postgres://brain_index:…@postgres:5432/appflowy
    OLLAMA_BASE                http://host.docker.internal:11434
    OLLAMA_EMBED_MODEL         nomic-embed-text
    OPENAI_API_KEY             optional; enables OpenAI embeddings when set
    OPENAI_EMBED_MODEL         text-embedding-3-small
    BRAIN_INDEX_TOKENS_FILE    /etc/sh-brain/index-tokens.json
    BRAIN_INDEX_HOST / PORT    default 127.0.0.1 / 28090
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import httpx
import numpy as np
import psycopg
from dataclasses import dataclass
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pgvector.psycopg import register_vector
from pydantic import BaseModel, Field

log = logging.getLogger("brain-index")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s brain-index %(message)s",
    stream=sys.stderr,
)

DB_URL = os.environ.get("BRAIN_INDEX_DB_URL", "postgres://brain_index:changeme@postgres:5432/appflowy")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY") or None
OPENAI_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
TOKENS_FILE = Path(os.environ.get("BRAIN_INDEX_TOKENS_FILE", "/etc/sh-brain/index-tokens.json"))

# Dimension is model-specific. We store a *column per model* as vectors of the
# right dim would require; for simplicity we standardize on the 768-dim
# nomic-embed-text column and store OpenAI vectors in a dedicated column.
NOMIC_DIM = 768
OPENAI_DIM = 1536


# ---------------------------------------------------------------------------
# DB lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.conn = await _connect()
    await _ensure_schema(app.state.conn)
    app.state.http = httpx.AsyncClient(timeout=60)
    log.info("brain-index ready db=%s ollama=%s openai=%s",
             _db_host(), OLLAMA_BASE, bool(OPENAI_KEY))
    try:
        yield
    finally:
        await app.state.http.aclose()
        await app.state.conn.close()


def _db_host() -> str:
    return DB_URL.split("@", 1)[-1].split("/", 1)[0]


async def _connect():
    conn = await psycopg.AsyncConnection.connect(DB_URL, autocommit=True)
    await register_vector(conn)
    return conn


async def _ensure_schema(conn: psycopg.AsyncConnection) -> None:
    schema_sql = (Path(__file__).parent / "schema.sql").read_text()
    async with conn.cursor() as cur:
        await cur.execute(schema_sql)


# ---------------------------------------------------------------------------
# Auth (bearer tokens, reloaded per request so rotation is instant)
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


@dataclass
class AgentInfo:
    agent: str                 # human-readable label (e.g. "claude-desktop")
    scopes: frozenset[str]     # subset of {"public", "personal", "ingest", "admin"}


DEFAULT_SCOPES = frozenset({"public"})


def _coerce_agent_info(raw: Any) -> AgentInfo | None:
    """Accept three legacy shapes for a token value:
        "claude-desktop"                                (string → public-only)
        {"agent": "claude", "scopes": ["public"]}       (preferred)
        {"agent": "claude", "scopes": "public,personal"}
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return AgentInfo(agent=raw, scopes=DEFAULT_SCOPES)
    if isinstance(raw, dict):
        agent = raw.get("agent") or raw.get("name")
        if not agent:
            return None
        scopes = raw.get("scopes") or []
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(",") if s.strip()]
        if not scopes:
            scopes = list(DEFAULT_SCOPES)
        return AgentInfo(agent=agent, scopes=frozenset(scopes))
    return None


def _load_tokens() -> dict[str, AgentInfo]:
    if not TOKENS_FILE.exists():
        return {}
    try:
        data = json.loads(TOKENS_FILE.read_text())
    except Exception as e:
        log.error("failed to parse %s: %s", TOKENS_FILE, e)
        return {}
    out: dict[str, AgentInfo] = {}
    for k, v in data.items():
        # Heuristic: tokens are always ≥ 32 chars, agent names are short labels.
        # If v is a dict, k must be the token; if v is a string, either side can be the token.
        if isinstance(v, dict):
            info = _coerce_agent_info(v)
            if info is not None:
                out[k] = info
        elif isinstance(v, str):
            if len(k) > len(v):
                info = _coerce_agent_info(v)
                if info is not None:
                    out[k] = info
            else:
                info = _coerce_agent_info(k)
                if info is not None:
                    out[v] = info
    return out


async def authenticate(creds: HTTPAuthorizationCredentials = Depends(security)) -> AgentInfo:
    if not creds or not creds.credentials:
        raise HTTPException(401, "missing bearer token")
    tokens = _load_tokens()
    info = tokens.get(creds.credentials)
    if not info:
        raise HTTPException(401, "invalid token")
    return info


def effective_agent(info: AgentInfo, request: Request) -> AgentInfo:
    """If the calling token is admin-scoped, honor an x-agent-override header
    so the upstream MCP can attribute the call to the real client agent."""
    if "admin" not in info.scopes:
        return info
    override_agent = request.headers.get("x-agent-override")
    override_scopes = request.headers.get("x-agent-scopes")
    if not override_agent:
        return info
    scopes = {s.strip() for s in (override_scopes or "").split(",") if s.strip()}
    if not scopes:
        scopes = set(DEFAULT_SCOPES)
    return AgentInfo(agent=override_agent, scopes=frozenset(scopes))


def require_scope(info: AgentInfo, *needed: str) -> None:
    if "admin" in info.scopes:
        return
    for n in needed:
        if n not in info.scopes:
            raise HTTPException(403, f"scope '{n}' required; token '{info.agent}' has {sorted(info.scopes)}")


# ---------------------------------------------------------------------------
# Audit logger
# ---------------------------------------------------------------------------

async def audit(
    request: Request,
    agent: AgentInfo,
    tool: str,
    *,
    query_prefix: str | None = None,
    result_count: int = 0,
    blocked: bool = False,
    scope_used: str | None = None,
    notes: str | None = None,
) -> None:
    try:
        ip = request.client.host if request.client else None
    except Exception:
        ip = None
    try:
        async with request.app.state.conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO brain_index.audit_log
                    (agent, tool, scope_used, query_prefix, result_count, blocked, source_ip, notes)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    agent.agent,
                    tool,
                    scope_used or ",".join(sorted(agent.scopes)),
                    (query_prefix or "")[:200],
                    result_count,
                    blocked,
                    ip,
                    notes,
                ),
            )
    except Exception as e:
        log.warning("audit write failed: %s", e)


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

async def _embed_ollama(client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for t in texts:
        r = await client.post(f"{OLLAMA_BASE}/api/embeddings", json={"model": OLLAMA_MODEL, "prompt": t})
        r.raise_for_status()
        out.append(r.json()["embedding"])
    return out


async def _embed_openai(client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
    if not OPENAI_KEY:
        raise HTTPException(400, "openai embeddings requested but OPENAI_API_KEY not set")
    r = await client.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={"model": OPENAI_MODEL, "input": texts},
    )
    r.raise_for_status()
    return [row["embedding"] for row in r.json()["data"]]


async def embed(client: httpx.AsyncClient, texts: list[str], prefer: str = "local") -> tuple[list[list[float]], str]:
    """Returns (vectors, model_used)."""
    if prefer == "openai" and OPENAI_KEY:
        return await _embed_openai(client, texts), OPENAI_MODEL
    try:
        return await _embed_ollama(client, texts), OLLAMA_MODEL
    except Exception as e:
        if OPENAI_KEY:
            log.warning("ollama failed (%s), falling back to openai", e)
            return await _embed_openai(client, texts), OPENAI_MODEL
        raise


# ---------------------------------------------------------------------------
# App + models
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sunheart Brain Index",
    description="Semantic index + dedup for Sunheart Brain. Backs the MCP server and exposes an OpenAPI surface for GPT Custom Connectors.",
    version="0.1.0",
    lifespan=lifespan,
)

from ingest_routes import router as ingest_router
app.include_router(ingest_router)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., description="One or more strings to embed")
    prefer: Literal["local", "openai"] = "local"


class EmbedResponse(BaseModel):
    model: str
    dim: int
    vectors: list[list[float]]


class UpsertNoteRequest(BaseModel):
    note_row_id: str = Field(..., description="AppFlowy row_id in '01 · Notes'")
    content: str
    source: str | None = None
    source_id: str | None = None
    tags: list[str] = []
    prefer: Literal["local", "openai"] = "local"


class SearchRequest(BaseModel):
    query: str
    k: int = 10
    source: str | None = None
    tags: list[str] | None = None
    prefer: Literal["local", "openai"] = "local"
    include_content: bool = True


class SearchHit(BaseModel):
    note_row_id: str
    chunk_idx: int
    score: float
    content: str | None = None
    source: str | None = None
    tags: list[str] = []
    sensitivity: str = "public"


class DedupRequest(BaseModel):
    threshold: float = Field(0.95, ge=0.5, le=1.0, description="Cosine similarity threshold for auto-merge")
    dry_run: bool = True
    limit: int = 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> dict:
    tokens = _load_tokens()
    return {
        "ok": True,
        "service": "brain-index",
        "version": app.version,
        "tokens_loaded": len(tokens),
        "ollama_base": OLLAMA_BASE,
        "ollama_model": OLLAMA_MODEL,
        "openai_enabled": bool(OPENAI_KEY),
    }


@app.post("/embed", response_model=EmbedResponse)
async def embed_route(req: EmbedRequest, request: Request, agent: AgentInfo = Depends(authenticate)) -> EmbedResponse:
    # /embed leaks nothing by itself, but guard against OpenAI routing for non-personal-cleared agents.
    prefer = req.prefer
    if prefer == "openai" and "personal" not in agent.scopes and "admin" not in agent.scopes:
        prefer = "local"  # silently downgrade — personal content must not hit OpenAI
    vectors, model = await embed(request.app.state.http, req.texts, prefer)
    return EmbedResponse(model=model, dim=len(vectors[0]) if vectors else 0, vectors=vectors)


@app.post("/upsert")
async def upsert_note(req: UpsertNoteRequest, request: Request, agent: AgentInfo = Depends(authenticate)) -> dict:
    require_scope(agent, "ingest")
    """Embed the note's content (chunked if needed) and upsert into note_chunks.
    Idempotent by (note_row_id, chunk_idx): re-running with the same content
    is a no-op (content_sha1 check)."""
    chunks = _chunk(req.content)
    vectors, model = await embed(request.app.state.http, chunks, req.prefer)
    conn = request.app.state.conn
    rows_written = 0
    async with conn.cursor() as cur:
        for idx, (text, vec) in enumerate(zip(chunks, vectors)):
            sha = hashlib.sha1(text.encode()).hexdigest()
            # Skip if nothing changed.
            await cur.execute(
                "SELECT content_sha1 FROM brain_index.note_chunks WHERE note_row_id=%s AND chunk_idx=%s",
                (req.note_row_id, idx),
            )
            existing = await cur.fetchone()
            if existing and existing[0] == sha:
                continue
            await cur.execute(
                """
                INSERT INTO brain_index.note_chunks
                    (note_row_id, chunk_idx, content, content_sha1, embedding, embedding_model, source, source_id, tags)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (note_row_id, chunk_idx) DO UPDATE SET
                    content         = EXCLUDED.content,
                    content_sha1    = EXCLUDED.content_sha1,
                    embedding       = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model,
                    tags            = EXCLUDED.tags
                """,
                (req.note_row_id, idx, text, sha, vec, model, req.source, req.source_id, req.tags),
            )
            rows_written += 1
    return {"ok": True, "chunks": len(chunks), "rows_written": rows_written, "model": model, "agent": agent}


@app.post("/search")
async def search(req: SearchRequest, request: Request, agent: AgentInfo = Depends(authenticate)) -> list[SearchHit]:
    agent = effective_agent(agent, request)
    allowed: list[str] = []
    if "public" in agent.scopes or "admin" in agent.scopes:
        allowed.append("public")
    if "personal" in agent.scopes or "admin" in agent.scopes:
        allowed.append("personal")
    # "private" is never returned — it should never have been stored.
    if not allowed:
        await audit(request, agent, "/search",
                    query_prefix=req.query, result_count=0, blocked=True,
                    notes="no public/personal scope")
        raise HTTPException(403, "token has neither 'public' nor 'personal' scope")

    # Force local embeddings for personal-scoped searches (avoid leaking via OpenAI).
    prefer = req.prefer
    if "personal" in allowed and "admin" not in agent.scopes:
        prefer = "local"

    vectors, _ = await embed(request.app.state.http, [req.query], prefer)
    vec = vectors[0]
    where = ["sensitivity = ANY(%s)"]
    params: list[Any] = [allowed]
    if req.source:
        where.append("source = %s")
        params.append(req.source)
    if req.tags:
        where.append("tags && %s")
        params.append(req.tags)
    sql = f"""
        SELECT note_row_id, chunk_idx, content, source, tags, sensitivity,
               1 - (embedding <=> %s) AS score
          FROM brain_index.note_chunks
         WHERE {' AND '.join(where)}
         ORDER BY embedding <=> %s
         LIMIT %s
    """
    conn = request.app.state.conn
    async with conn.cursor() as cur:
        await cur.execute(sql, [vec, *params, vec, req.k])
        rows = await cur.fetchall()
    hits = [
        SearchHit(
            note_row_id=r[0],
            chunk_idx=r[1],
            content=r[2] if req.include_content else None,
            source=r[3],
            tags=list(r[4] or []),
            sensitivity=r[5] or "public",
            score=float(r[6]),
        )
        for r in rows
    ]
    await audit(request, agent, "/search",
                query_prefix=req.query, result_count=len(hits),
                scope_used=",".join(allowed))
    return hits


@app.post("/dedup")
async def dedup(req: DedupRequest, request: Request, agent: AgentInfo = Depends(authenticate)) -> dict:
    require_scope(agent, "ingest")
    """Find near-duplicate chunks above the threshold, propose concept merges.
    Non-destructive by default (dry_run=True)."""
    conn = request.app.state.conn
    proposals: list[dict] = []
    async with conn.cursor() as cur:
        # Self-join: chunk pairs with cosine >= threshold, capped to req.limit.
        await cur.execute(
            """
            WITH pairs AS (
                SELECT a.id AS a_id, b.id AS b_id,
                       a.note_row_id AS a_note, b.note_row_id AS b_note,
                       1 - (a.embedding <=> b.embedding) AS score
                  FROM brain_index.note_chunks a
                  JOIN brain_index.note_chunks b ON a.id < b.id
                 WHERE a.embedding IS NOT NULL AND b.embedding IS NOT NULL
                   AND 1 - (a.embedding <=> b.embedding) >= %s
                 ORDER BY score DESC
                 LIMIT %s
            )
            SELECT * FROM pairs
            """,
            (req.threshold, req.limit),
        )
        rows = await cur.fetchall()
        for a_id, b_id, a_note, b_note, score in rows:
            proposals.append({
                "a": str(a_id), "a_note": a_note,
                "b": str(b_id), "b_note": b_note,
                "score": float(score),
            })
    if not req.dry_run:
        # Execution path: create/attach concepts, log merges. Kept minimal here;
        # the richer merge logic lives in the MCP `brain_merge_concepts` tool,
        # which calls back into us with explicit ids.
        log.warning("dedup called with dry_run=False; actual merges must go through brain_merge_concepts")
    return {"proposals": proposals, "threshold": req.threshold, "dry_run": req.dry_run}


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

CHUNK_CHARS = 3000      # ~750 tokens, safely under nomic-embed-text's 8k window


def _chunk(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return [""]
    if len(text) <= CHUNK_CHARS:
        return [text]
    # Prefer paragraph boundaries when we can.
    out: list[str] = []
    buf: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        if size + len(para) + 2 > CHUNK_CHARS and buf:
            out.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(para)
        size += len(para) + 2
    if buf:
        out.append("\n\n".join(buf))
    return out


# ---------------------------------------------------------------------------
# Entrypoint (uvicorn app:app when run directly; systemd unit uses this)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("BRAIN_INDEX_HOST", "127.0.0.1"),
        port=int(os.environ.get("BRAIN_INDEX_PORT", "28090")),
        log_level="info",
    )
