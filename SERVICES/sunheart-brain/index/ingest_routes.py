"""
brain-index — ingest routes.

Thin wrapper around AppFlowy Cloud + the pgvector index that the
brain-ingest CLI calls. Keeps AppFlowy creds + the MCP's write-stamping
logic out of the user's laptop.

Flow for add_note:
    1. Dedup check: if (source, source_id) already in note_chunks, return existing row_id (idempotent).
    2. Create AppFlowy row in '01 · Notes' via REST.
    3. Embed + upsert into note_chunks (calls /upsert internally).
    4. Return the new row_id.

ensure_conversation is similar but against '03 · Conversations'.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("brain-index.ingest")

APPFLOWY_BASE     = os.environ.get("SH_APPFLOWY_BASE", "http://sh-brain-nginx/")  # internal docker alias
APPFLOWY_EMAIL    = os.environ.get("SH_MCP_USER", "james.rick.stinson@gmail.com")
APPFLOWY_PASSWORD = os.environ.get("SH_MCP_PASSWORD")
WORKSPACE_ID      = os.environ.get("SH_WORKSPACE_ID")

DB_NAMES = {
    "notes":         "01 · Notes",
    "conversations": "03 · Conversations",
    "sources":       "04 · Sources",
    "tags":          "05 · Tags",
    "concepts":      "02 · Concepts",
}


# ---------------------------------------------------------------------------
# AppFlowy client (minimal — just login + discover + add_row)
# ---------------------------------------------------------------------------

@dataclass
class _AF:
    base: str
    email: str
    password: str
    workspace_id: str
    token: str | None = None
    db_ids: dict[str, str] = field(default_factory=dict)
    fields_by_db: dict[str, dict[str, dict]] = field(default_factory=dict)
    http: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=30))

    async def login(self):
        r = await self.http.post(
            f"{self.base}/gotrue/token?grant_type=password",
            json={"email": self.email, "password": self.password},
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]

    async def _req(self, method, path, **kw):
        r = await self.http.request(
            method, f"{self.base}{path}",
            headers={"Authorization": f"Bearer {self.token}"},
            **kw,
        )
        if r.status_code == 401:
            await self.login()
            r = await self.http.request(
                method, f"{self.base}{path}",
                headers={"Authorization": f"Bearer {self.token}"},
                **kw,
            )
        r.raise_for_status()
        return r.json() if r.content else None

    async def discover(self):
        folder = await self._req("GET", f"/api/workspace/{self.workspace_id}/folder?depth=8")
        root = folder.get("data", folder)
        name_to_vids: dict[str, list[str]] = {}

        def walk(node, matched=None):
            n = (node.get("name") or "").strip()
            cur = matched
            if n in DB_NAMES.values():
                cur = n
            if cur and node.get("view_id"):
                name_to_vids.setdefault(cur, []).append(node["view_id"])
            for c in node.get("children") or []:
                walk(c, cur)

        walk(root)
        dbs = await self._req("GET", f"/api/workspace/{self.workspace_id}/database")
        dbs_list = dbs.get("data") if isinstance(dbs, dict) else dbs
        view_to_db = {}
        for d in dbs_list or []:
            for v in d.get("views") or []:
                vid = v["view_id"] if isinstance(v, dict) else v
                view_to_db[vid] = d["id"]
        for key, fullname in DB_NAMES.items():
            for vid in name_to_vids.get(fullname, []):
                if vid in view_to_db:
                    self.db_ids[key] = view_to_db[vid]
                    break

    async def fields(self, db_key: str) -> dict[str, dict]:
        if db_key in self.fields_by_db:
            return self.fields_by_db[db_key]
        db_id = self.db_ids[db_key]
        data = await self._req("GET", f"/api/workspace/{self.workspace_id}/database/{db_id}/fields")
        fields_list = data.get("data") or data
        self.fields_by_db[db_key] = {f["name"]: f for f in fields_list}
        return self.fields_by_db[db_key]

    async def add_row(self, db_key: str, cells_by_name: dict) -> str:
        db_id = self.db_ids[db_key]
        fs = await self.fields(db_key)
        from app import _render_cell  # reuse the one in app.py
        cells = {}
        for name, val in cells_by_name.items():
            f = fs.get(name)
            if not f:
                log.warning("unknown field %r for %s", name, db_key)
                continue
            cells[f["id"]] = _render_cell(f, val)
        out = await self._req(
            "POST",
            f"/api/workspace/{self.workspace_id}/database/{db_id}/row",
            json={"cells": cells},
        )
        if isinstance(out, dict):
            data = out.get("data") or {}
            return data.get("id") or out.get("id") or ""
        return ""

    async def find_row_by_source_id(self, db_key: str, source_id_field: str, source_id_value: str) -> str | None:
        """Linear scan. Acceptable for now (pagination would be better at >10k rows)."""
        db_id = self.db_ids[db_key]
        ids_resp = await self._req("GET", f"/api/workspace/{self.workspace_id}/database/{db_id}/row")
        ids_list = (ids_resp.get("data") if isinstance(ids_resp, dict) else ids_resp) or []
        row_ids = [r["id"] for r in ids_list if r.get("id")]
        # Batched detail fetch
        CHUNK = 50
        for i in range(0, len(row_ids), CHUNK):
            batch = row_ids[i:i+CHUNK]
            detail = await self._req(
                "GET",
                f"/api/workspace/{self.workspace_id}/database/{db_id}/row/detail",
                params={"ids": ",".join(batch)},
            )
            rows = (detail.get("data") if isinstance(detail, dict) else detail) or []
            for r in rows:
                cells = r.get("cells") or {}
                if str(cells.get(source_id_field, "")) == source_id_value:
                    return r["id"]
        return None


_af: _AF | None = None


async def get_af() -> _AF:
    global _af
    if _af is None:
        if not APPFLOWY_PASSWORD or not WORKSPACE_ID:
            raise HTTPException(500, "SH_MCP_PASSWORD / SH_WORKSPACE_ID not configured on brain-index")
        _af = _AF(
            base=APPFLOWY_BASE.rstrip("/"),
            email=APPFLOWY_EMAIL,
            password=APPFLOWY_PASSWORD,
            workspace_id=WORKSPACE_ID,
        )
        await _af.login()
        await _af.discover()
        log.info("brain-index/ingest: %d/%d dbs resolved", len(_af.db_ids), len(DB_NAMES))
    return _af


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/ingest", tags=["ingest"])


class AddNoteReq(BaseModel):
    source: str
    source_id: str
    title: str | None = None
    content: str
    tags: list[str] = []
    note_type: str | None = None
    source_url: str | None = None
    original_created_at: str | None = None
    conversation_row_id: str | None = None
    prefer: str = "local"
    sensitivity: str = "🟢 Public"   # one of 🟢 Public | 🟡 Personal | 🔴 Private
    pii_flags: list[str] = []


class AddNoteResp(BaseModel):
    note_row_id: str
    created: bool
    embedded: bool


class EnsureConvReq(BaseModel):
    source: str
    external_id: str
    title: str
    started_at: str | None = None


class EnsureConvResp(BaseModel):
    conversation_row_id: str
    created: bool


def _sensitivity_to_db(label: str) -> str:
    """Map the AppFlowy emoji label to the lowercase code used in note_chunks.sensitivity."""
    if "Personal" in label: return "personal"
    if "Private" in label:  return "private"
    return "public"


async def _auth(request: Request):
    """Extract + verify bearer token and return an AgentInfo."""
    from app import authenticate
    from fastapi.security import HTTPAuthorizationCredentials
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth_header.split(" ", 1)[1])
    return await authenticate(creds)


@router.post("/add_note", response_model=AddNoteResp)
async def add_note(req: AddNoteReq, request: Request):
    from app import require_scope, audit
    agent = await _auth(request)
    require_scope(agent, "ingest")

    sens_db = _sensitivity_to_db(req.sensitivity)
    # 🔴 Private never gets stored — that's the point of the tiering.
    if sens_db == "private":
        await audit(request, agent, "/ingest/add_note",
                    query_prefix=req.title or req.content[:80],
                    result_count=0, blocked=True,
                    notes="private tier — refused at ingest")
        raise HTTPException(400, "Private-tier notes must not be sent to the brain")

    # Never use OpenAI for personal-tier content.
    prefer = "local" if sens_db == "personal" else req.prefer

    af = await get_af()

    # Idempotent by (source, source_id).
    existing = await af.find_row_by_source_id("notes", "Source ID", req.source_id)
    created = False
    if not existing:
        cells: dict[str, Any] = {
            "Title": req.title or (req.content[:80] + ("…" if len(req.content) > 80 else "")),
            "Content": req.content,
            "Source": req.source,
            "Source ID": req.source_id,
            "Dedup Status": "🆕 New",
            "Sensitivity": req.sensitivity,
        }
        if req.pii_flags:           cells["PII Flags"] = req.pii_flags
        if req.source_url:          cells["Source URL"] = req.source_url
        if req.original_created_at: cells["Original Created At"] = req.original_created_at
        if req.tags:                cells["Tags"] = req.tags
        if req.note_type:           cells["Note Type"] = req.note_type
        existing = await af.add_row("notes", cells)
        created = True

    embedded = False
    if existing:
        from app import embed as do_embed
        try:
            vecs, model = await do_embed(request.app.state.http, [req.content], prefer)
            sha = hashlib.sha1(req.content.encode()).hexdigest()
            async with request.app.state.conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.note_chunks
                        (note_row_id, chunk_idx, content, content_sha1, embedding, embedding_model,
                         source, source_id, tags, sensitivity, pii_flags)
                    VALUES (%s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (note_row_id, chunk_idx) DO UPDATE SET
                        content=EXCLUDED.content, content_sha1=EXCLUDED.content_sha1,
                        embedding=EXCLUDED.embedding, embedding_model=EXCLUDED.embedding_model,
                        tags=EXCLUDED.tags, sensitivity=EXCLUDED.sensitivity, pii_flags=EXCLUDED.pii_flags
                    """,
                    (existing, req.content, sha, vecs[0], model,
                     req.source, req.source_id, req.tags, sens_db, req.pii_flags),
                )
            embedded = True
        except Exception as e:
            log.warning("embed failed for %s/%s: %s", req.source, req.source_id, e)

    await audit(request, agent, "/ingest/add_note",
                query_prefix=(req.title or req.content[:60]),
                result_count=1 if created else 0,
                notes=f"sensitivity={sens_db} embedded={embedded}")
    return AddNoteResp(note_row_id=existing or "", created=created, embedded=embedded)


@router.post("/ensure_conversation", response_model=EnsureConvResp)
async def ensure_conversation(req: EnsureConvReq, request: Request):
    from app import require_scope
    agent = await _auth(request)
    require_scope(agent, "ingest")
    af = await get_af()
    existing = await af.find_row_by_source_id("conversations", "External ID", req.external_id)
    if existing:
        return EnsureConvResp(conversation_row_id=existing, created=False)
    cells: dict[str, Any] = {
        "Title": req.title,
        "Source": req.source,
        "External ID": req.external_id,
        "Status": "📥 Imported",
    }
    if req.started_at:
        cells["Started At"] = req.started_at
    row_id = await af.add_row("conversations", cells)
    return EnsureConvResp(conversation_row_id=row_id, created=True)
