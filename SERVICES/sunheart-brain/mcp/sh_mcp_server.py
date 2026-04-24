"""
Sunheart Brain — MCP Server
============================

Exposes the 5 AppFlowy databases + the pgvector semantic index as MCP
tools. Claude Desktop / Claude Code / Cursor / (GPT via Custom
Connector) all point at the same server.

Transport: stdio by default; HTTPS+SSE via sh_mcp_http.py wrapper.

Auth model: single AppFlowy service account (env SH_MCP_USER /
SH_MCP_PASSWORD) + a bearer token per agent at the HTTP layer. The
token's agent name is stamped into every write via `agent_ctx`.

Env:
    SH_APPFLOWY_BASE     https://brain.sunheart.com
    SH_MCP_USER          james.rick.stinson@gmail.com
    SH_MCP_PASSWORD      (required)
    SH_WORKSPACE_ID      (required — captured during provisioning)
    SH_INDEX_BASE        http://127.0.0.1:28090   (brain-index REST base)
    SH_INDEX_TOKEN       (required — matches a token in brain-index/tokens.json)
    SH_MCP_AGENT         default identity when not in HTTP mode
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

agent_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("sh_agent", default=None)
scopes_ctx: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar("sh_scopes", default=frozenset({"public"}))


def _effective_scopes() -> frozenset[str]:
    return scopes_ctx.get() or frozenset({"public"})


def _require_scope(*needed: str) -> None:
    scopes = _effective_scopes()
    if "admin" in scopes:
        return
    missing = [n for n in needed if n not in scopes]
    if missing:
        raise PermissionError(
            f"token for agent '{_effective_agent()}' lacks scope(s) {missing}; has {sorted(scopes)}"
        )


def _allowed_sensitivities() -> list[str]:
    """Which sensitivity tiers this caller is allowed to READ."""
    s = _effective_scopes()
    allowed: list[str] = []
    if "public" in s or "admin" in s: allowed.append("public")
    if "personal" in s or "admin" in s: allowed.append("personal")
    return allowed


log = logging.getLogger("sh-mcp")
logging.basicConfig(
    level=os.environ.get("SH_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s sh-mcp %(message)s",
    stream=sys.stderr,
)

APPFLOWY_BASE = os.environ.get("SH_APPFLOWY_BASE", "https://brain.sunheart.com")
SVC_USER = os.environ.get("SH_MCP_USER", "james.rick.stinson@gmail.com")
SVC_PASSWORD = os.environ.get("SH_MCP_PASSWORD")
WORKSPACE_ID = os.environ.get("SH_WORKSPACE_ID")
AGENT = os.environ.get("SH_MCP_AGENT", "unspecified")

INDEX_BASE = os.environ.get("SH_INDEX_BASE", "http://127.0.0.1:28090")
INDEX_TOKEN = os.environ.get("SH_INDEX_TOKEN")


def _effective_agent() -> str:
    return agent_ctx.get() or AGENT


DB_SPEC = [
    ("notes",         "01 · Notes"),
    ("concepts",      "02 · Concepts"),
    ("conversations", "03 · Conversations"),
    ("sources",       "04 · Sources"),
    ("tags",          "05 · Tags"),
]
DB_NAME_BY_KEY = dict(DB_SPEC)


# ---------------------------------------------------------------------------
# AppFlowy client (same pattern as zen-village's zv_mcp_server; light fork)
# ---------------------------------------------------------------------------

@dataclass
class AppFlowyClient:
    base: str
    email: str
    password: str
    workspace_id: str
    access_token: str | None = None
    refresh_token: str | None = None
    db_ids: dict[str, str] = field(default_factory=dict)
    db_views: dict[str, str] = field(default_factory=dict)
    db_fields: dict[str, dict[str, dict]] = field(default_factory=dict)
    client: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=30))

    async def login(self) -> None:
        r = await self.client.post(
            f"{self.base}/gotrue/token?grant_type=password",
            json={"email": self.email, "password": self.password},
        )
        r.raise_for_status()
        j = r.json()
        self.access_token = j["access_token"]
        self.refresh_token = j["refresh_token"]
        log.info("Logged in as %s", self.email)

    def _h(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _req(self, method: str, path: str, **kw) -> Any:
        r = await self.client.request(method, f"{self.base}{path}", headers=self._h(), **kw)
        if r.status_code == 401:
            await self.login()
            r = await self.client.request(method, f"{self.base}{path}", headers=self._h(), **kw)
        r.raise_for_status()
        return r.json() if r.content else None

    async def discover_db_ids(self) -> None:
        folder = await self._req("GET", f"/api/workspace/{self.workspace_id}/folder?depth=8")
        root = folder.get("data", folder)
        name_to_vids: dict[str, list[str]] = {}

        def walk(node: dict, matched: str | None = None) -> None:
            n = (node.get("name") or "").strip()
            cur = matched
            if n in DB_NAME_BY_KEY.values():
                cur = n
            if cur and node.get("view_id"):
                name_to_vids.setdefault(cur, []).append(node["view_id"])
            for c in node.get("children") or []:
                walk(c, cur)

        walk(root)

        dbs = await self._req("GET", f"/api/workspace/{self.workspace_id}/database")
        dbs_list = dbs.get("data") if isinstance(dbs, dict) else dbs
        view_to_db: dict[str, str] = {}
        for d in dbs_list or []:
            for v in d.get("views") or []:
                vid = v["view_id"] if isinstance(v, dict) else v
                view_to_db[vid] = d["id"]
        for key, name in DB_SPEC:
            for vid in name_to_vids.get(name, []):
                if vid in view_to_db:
                    self.db_ids[key] = view_to_db[vid]
                    self.db_views[key] = vid
                    break
            if key not in self.db_ids:
                log.warning("Could not resolve %r (candidates=%s)", name, name_to_vids.get(name))
        log.info("Resolved %d/%d databases", len(self.db_ids), len(DB_SPEC))

    def db_url(self, db_key: str) -> str:
        vid = self.db_views.get(db_key)
        return f"{self.base}/app/{self.workspace_id}/{vid}" if vid else self.base

    async def get_fields(self, db_key: str) -> dict[str, dict]:
        if db_key in self.db_fields:
            return self.db_fields[db_key]
        db_id = self.db_ids[db_key]
        data = await self._req("GET", f"/api/workspace/{self.workspace_id}/database/{db_id}/fields")
        fields_list = data.get("data") or data
        self.db_fields[db_key] = {f["name"]: f for f in fields_list}
        return self.db_fields[db_key]

    async def list_rows(self, db_key: str, limit: int = 50) -> list[dict]:
        db_id = self.db_ids[db_key]
        ids_resp = await self._req("GET", f"/api/workspace/{self.workspace_id}/database/{db_id}/row")
        ids_list = (ids_resp.get("data") if isinstance(ids_resp, dict) else ids_resp) or []
        row_ids = [r["id"] for r in ids_list if r.get("id")][:limit]
        if not row_ids:
            return []
        detail = await self._req(
            "GET",
            f"/api/workspace/{self.workspace_id}/database/{db_id}/row/detail",
            params={"ids": ",".join(row_ids)},
        )
        rows = (detail.get("data") if isinstance(detail, dict) else detail) or []
        by_id = {r["id"]: r for r in rows}
        out: list[dict] = []
        for rid in row_ids:
            r = by_id.get(rid, {"id": rid, "cells": {}})
            pretty: dict[str, Any] = {"row_id": r["id"]}
            for n, v in (r.get("cells") or {}).items():
                pretty[n] = _simplify_cell(v)
            out.append(pretty)
        return out

    async def add_row(self, db_key: str, cells_by_name: dict[str, Any], stamp: bool = True) -> dict:
        db_id = self.db_ids[db_key]
        fields = await self.get_fields(db_key)
        if stamp:
            targets = ["Notes", "Summary", "Description"]
            who = _effective_agent()
            s = f"[via {who} @ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}]"
            for t in targets:
                if t in fields:
                    prev = cells_by_name.get(t, "")
                    cells_by_name[t] = f"{s} {prev}".strip() if prev else s
                    break
        cells = {}
        for name, val in cells_by_name.items():
            f = fields.get(name)
            if not f:
                log.warning("Ignoring unknown field %r for %s", name, db_key)
                continue
            cells[f["id"]] = _render_cell(f, val)
        log.info("add_row db=%s agent=%s fields=%s", db_key, _effective_agent(), list(cells_by_name.keys()))
        return await self._req(
            "POST",
            f"/api/workspace/{self.workspace_id}/database/{db_id}/row",
            json={"cells": cells},
        )


def _simplify_cell(value: Any) -> Any:
    if isinstance(value, dict) and ("start" in value or "pretty_start_datetime" in value):
        return value.get("pretty_start_datetime") or value.get("start")
    return value


def _field_kind(field_meta: dict) -> str:
    ft = field_meta.get("field_type")
    if isinstance(ft, str):
        return ft
    fid = field_meta.get("field_type_id", ft)
    return {0: "RichText", 1: "Number", 2: "DateTime", 3: "SingleSelect",
            4: "MultiSelect", 5: "Checkbox", 6: "URL", 7: "Checkbox",
            10: "Relation"}.get(fid, "RichText")


def _select_options(field_meta: dict) -> list[dict]:
    to = field_meta.get("type_option") or {}
    c = to.get("content")
    if isinstance(c, dict) and isinstance(c.get("options"), list):
        return c["options"]
    if isinstance(c, str):
        try:
            j = json.loads(c)
            if isinstance(j, dict) and isinstance(j.get("options"), list):
                return j["options"]
        except Exception:
            pass
    if isinstance(to.get("options"), list):
        return to["options"]
    return []


def _render_cell(field_meta: dict, value: Any) -> Any:
    if value is None:
        return ""
    kind = _field_kind(field_meta)
    if kind == "RichText" or kind == "URL":
        return str(value)
    if kind == "Number":
        return str(value)
    if kind == "DateTime":
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return str(value)
    if kind == "Checkbox":
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value)
    if kind == "SingleSelect":
        for o in _select_options(field_meta):
            if str(o.get("name", "")).lower() == str(value).lower():
                return o["id"]
        log.warning("SingleSelect %r: value %r not in options", field_meta.get("name"), value)
        return str(value)
    if kind == "MultiSelect":
        opts = _select_options(field_meta)
        m = {str(o.get("name", "")).lower(): o["id"] for o in opts}
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",") if v.strip()]
        ids = []
        for v in value:
            sid = m.get(str(v).lower())
            ids.append(sid if sid else str(v))
        return ",".join(ids)
    return str(value)


# ---------------------------------------------------------------------------
# brain-index client
# ---------------------------------------------------------------------------

async def index_call(method: str, path: str, json_body: dict | None = None) -> Any:
    if not INDEX_TOKEN:
        raise RuntimeError("SH_INDEX_TOKEN not set — cannot call brain-index")
    headers = {"Authorization": f"Bearer {INDEX_TOKEN}"}
    # Forward the real calling agent + their scopes to brain-index for
    # accurate audit attribution + server-side sensitivity filtering.
    agent = _effective_agent()
    if agent:
        headers["x-agent-override"] = agent
        headers["x-agent-scopes"] = ",".join(sorted(_effective_scopes()))
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.request(
            method,
            f"{INDEX_BASE}{path}",
            headers=headers,
            json=json_body,
        )
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

server = Server("sunheart-brain")
client: AppFlowyClient | None = None


async def _ensure_ready() -> AppFlowyClient:
    global client
    if client is None:
        if not SVC_PASSWORD:
            raise RuntimeError("SH_MCP_PASSWORD not set")
        if not WORKSPACE_ID:
            raise RuntimeError("SH_WORKSPACE_ID not set")
        client = AppFlowyClient(
            base=APPFLOWY_BASE, email=SVC_USER,
            password=SVC_PASSWORD, workspace_id=WORKSPACE_ID,
        )
        await client.login()
        await client.discover_db_ids()
    return client


TOOLS: list[Tool] = [
    Tool(name="brain_status",
         description="Health check: which Sunheart Brain databases are reachable, row counts, brain-index status.",
         inputSchema={"type": "object", "properties": {}, "required": []}),
    Tool(name="brain_list",
         description=(
             "List rows from a Sunheart Brain database (notes | concepts | conversations | sources | tags). "
             "For text/semantic search of Notes, prefer brain_search_semantic."
         ),
         inputSchema={
             "type": "object",
             "properties": {
                 "db":    {"type": "string", "enum": [k for k, _ in DB_SPEC]},
                 "limit": {"type": "integer", "default": 25, "minimum": 1, "maximum": 200},
             },
             "required": ["db"],
         }),
    Tool(name="brain_get_note",
         description="Fetch a single note by row_id from 01 · Notes. Returns all cells hydrated.",
         inputSchema={
             "type": "object",
             "properties": {"row_id": {"type": "string"}},
             "required": ["row_id"],
         }),
    Tool(name="brain_search_text",
         description="Keyword (case-insensitive substring) search across a brain database. Fast, exact.",
         inputSchema={
             "type": "object",
             "properties": {
                 "db": {"type": "string", "enum": [k for k, _ in DB_SPEC], "default": "notes"},
                 "query": {"type": "string"},
                 "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
             },
             "required": ["query"],
         }),
    Tool(name="brain_search_semantic",
         description=(
             "Semantic (embedding-based) search across Notes. Use this when you want "
             "things that MEAN the query, not just contain the words. Backed by pgvector."
         ),
         inputSchema={
             "type": "object",
             "properties": {
                 "query": {"type": "string"},
                 "k":     {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                 "source": {"type": "string", "description": "Optional: restrict to Bear | ChatGPT | Claude | Cursor | Manual"},
                 "tags":   {"type": "array", "items": {"type": "string"}, "description": "Optional: rows must have ALL these tags"},
                 "prefer": {"type": "string", "enum": ["local", "openai"], "default": "local"},
             },
             "required": ["query"],
         }),
    Tool(name="brain_add_note",
         description=(
             "Add a row to 01 · Notes. Creates the AppFlowy row AND kicks off an "
             "embedding upsert into brain-index (so the note is semantically searchable "
             "within seconds)."
         ),
         inputSchema={
             "type": "object",
             "properties": {
                 "title":               {"type": "string", "description": "Short title; defaults to first 80 chars of content"},
                 "content":             {"type": "string"},
                 "source":              {"type": "string", "description": "Bear | ChatGPT | Claude | Cursor | Manual | Web | Other"},
                 "source_id":           {"type": "string"},
                 "source_url":          {"type": "string"},
                 "original_created_at": {"type": "string", "description": "ISO 8601"},
                 "tags":                {"type": "array", "items": {"type": "string"}},
                 "note_type":           {"type": "string", "description": "User Message | AI Response | Journal | Reference | Snippet | Idea | Conversation Turn"},
                 "linked_conversation": {"type": "string", "description": "row_id of a Conversations row"},
             },
             "required": ["content"],
         }),
    Tool(name="brain_add_concept",
         description="Add a canonical concept to 02 · Concepts.",
         inputSchema={
             "type": "object",
             "properties": {
                 "concept":     {"type": "string"},
                 "description": {"type": "string"},
                 "aliases":     {"type": "array", "items": {"type": "string"}},
                 "domain":      {"type": "array", "items": {"type": "string"}},
                 "salience":    {"type": "string", "description": "⭐ Core | 🔵 Active | 🟡 Dormant | ⚫ Archived"},
             },
             "required": ["concept"],
         }),
    Tool(name="brain_add_conversation",
         description="Register an AI chat thread in 03 · Conversations. Creates the parent row; use brain_add_note for each message.",
         inputSchema={
             "type": "object",
             "properties": {
                 "title":       {"type": "string"},
                 "source":      {"type": "string", "description": "ChatGPT | Claude | Cursor | Grok | Perplexity | Other"},
                 "external_id": {"type": "string"},
                 "source_url":  {"type": "string"},
                 "started_at":  {"type": "string"},
                 "last_message_at": {"type": "string"},
                 "message_count":   {"type": "integer"},
                 "summary":     {"type": "string"},
             },
             "required": ["title", "source"],
         }),
    Tool(name="brain_propose_dedup",
         description=(
             "Run the dedup pass over brain-index. Returns a list of "
             "{a_note, b_note, score} pairs above the threshold. Non-destructive; "
             "use brain_merge_concepts to act on them."
         ),
         inputSchema={
             "type": "object",
             "properties": {
                 "threshold": {"type": "number", "default": 0.95, "minimum": 0.5, "maximum": 1.0},
                 "limit":     {"type": "integer", "default": 200, "minimum": 1, "maximum": 2000},
             },
         }),
    Tool(name="brain_merge_concepts",
         description=(
             "Merge one or more source concepts into a target canonical concept. Updates "
             "concept links on all their notes. Writes a row to the merge_log for audit."
         ),
         inputSchema={
             "type": "object",
             "properties": {
                 "keep_concept_row_id":   {"type": "string", "description": "The concept to KEEP"},
                 "merge_concept_row_ids": {"type": "array", "items": {"type": "string"}, "description": "Concepts to merge INTO the keeper"},
                 "reason":                {"type": "string"},
             },
             "required": ["keep_concept_row_id", "merge_concept_row_ids"],
         }),
    Tool(name="brain_propose_tag",
         description="Propose a new tag to 05 · Tags with Status = '🟡 Proposed'. Later a weekly review promotes or merges.",
         inputSchema={
             "type": "object",
             "properties": {
                 "tag":         {"type": "string"},
                 "description": {"type": "string"},
                 "parent_tag":  {"type": "string", "description": "Optional: row_id of parent tag"},
             },
             "required": ["tag"],
         }),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    c = await _ensure_ready()
    a = arguments or {}

    if name == "brain_status":
        lines = [f"AppFlowy base:   {APPFLOWY_BASE}",
                 f"Service account: {SVC_USER}",
                 f"Index base:      {INDEX_BASE}", ""]
        for key, full in DB_SPEC:
            if key in c.db_ids:
                try:
                    rows = await c.list_rows(key, limit=200)
                    lines.append(f"  {full:22s} → {len(rows)} rows")
                except Exception as e:
                    lines.append(f"  {full:22s} → ERROR {e}")
            else:
                lines.append(f"  {full:22s} → (not resolved)")
        try:
            h = await index_call("GET", "/healthz")
            lines.append(f"\nbrain-index:     ok={h.get('ok')} ollama={h.get('ollama_model')} openai={h.get('openai_enabled')}")
        except Exception as e:
            lines.append(f"\nbrain-index:     ERROR {e}")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "brain_list":
        rows = await c.list_rows(a["db"], limit=int(a.get("limit", 25)))
        return [TextContent(type="text", text=json.dumps(rows, indent=2, default=str))]

    if name == "brain_get_note":
        rid = a["row_id"]
        db_id = c.db_ids["notes"]
        detail = await c._req(
            "GET",
            f"/api/workspace/{c.workspace_id}/database/{db_id}/row/detail",
            params={"ids": rid},
        )
        rows = (detail.get("data") if isinstance(detail, dict) else detail) or []
        if not rows:
            return [TextContent(type="text", text=f"No note with id {rid}")]
        r = rows[0]
        pretty = {"row_id": r["id"], **{n: _simplify_cell(v) for n, v in (r.get("cells") or {}).items()}}
        return [TextContent(type="text", text=json.dumps(pretty, indent=2, default=str))]

    if name == "brain_search_text":
        db = a.get("db", "notes")
        q = a["query"].lower()
        limit = int(a.get("limit", 20))
        rows = await c.list_rows(db, limit=500)
        def matches(r: dict) -> bool:
            for v in r.values():
                if isinstance(v, str) and q in v.lower():
                    return True
                if isinstance(v, list):
                    for x in v:
                        if isinstance(x, str) and q in x.lower():
                            return True
            return False
        hits = [r for r in rows if matches(r)][:limit]
        return [TextContent(type="text", text=json.dumps(hits, indent=2, default=str))]

    if name == "brain_search_semantic":
        allowed = _allowed_sensitivities()
        if not allowed:
            return [TextContent(type="text", text=(
                "Denied: this token has neither 'public' nor 'personal' scope. "
                "Ask for an upgraded token to see personal content."
            ))]
        # personal content must never be embedded by openai (to avoid leaking the query)
        prefer = a.get("prefer", "local")
        if "personal" in allowed and prefer == "openai":
            prefer = "local"
        body = {
            "query": a["query"],
            "k": int(a.get("k", 10)),
            "prefer": prefer,
            "include_content": True,
        }
        if a.get("source"):
            body["source"] = a["source"]
        if a.get("tags"):
            body["tags"] = a["tags"]
        hits = await index_call("POST", "/search", body)
        return [TextContent(type="text", text=json.dumps(hits, indent=2, default=str))]

    if name == "brain_add_note":
        try:
            _require_scope("ingest")
        except PermissionError as e:
            return [TextContent(type="text", text=f"Denied: {e}")]
        title = a.get("title") or (a["content"][:80] + ("…" if len(a["content"]) > 80 else ""))
        cells: dict[str, Any] = {"Title": title, "Content": a["content"]}
        if "source"              in a: cells["Source"] = a["source"]
        if "source_id"           in a: cells["Source ID"] = a["source_id"]
        if "source_url"          in a: cells["Source URL"] = a["source_url"]
        if "original_created_at" in a: cells["Original Created At"] = a["original_created_at"]
        if "tags"                in a: cells["Tags"] = a["tags"]
        if "note_type"           in a: cells["Note Type"] = a["note_type"]
        cells["Dedup Status"] = "🆕 New"
        out = await c.add_row("notes", cells, stamp=False)
        row_id = _extract_row_id(out)
        # Fire embedding upsert (best-effort; failure shouldn't block the write).
        embedded_ok = False
        try:
            await index_call("POST", "/upsert", {
                "note_row_id": row_id,
                "content": a["content"],
                "source": a.get("source"),
                "source_id": a.get("source_id"),
                "tags": a.get("tags", []),
            })
            embedded_ok = True
        except Exception as e:
            log.warning("embedding upsert failed for %s: %s", row_id, e)
        return [TextContent(type="text", text=(
            f"OK — added note '{title}' (row_id={row_id}, embedded={embedded_ok})"
        ))]

    if name == "brain_add_concept":
        cells: dict[str, Any] = {"Concept": a["concept"]}
        if "description" in a: cells["Description"] = a["description"]
        if "aliases"     in a: cells["Aliases"] = "\n".join(a["aliases"])
        if "domain"      in a: cells["Domain"] = a["domain"]
        if "salience"    in a: cells["Salience"] = a["salience"]
        out = await c.add_row("concepts", cells)
        return [TextContent(type="text", text=f"OK — added concept '{a['concept']}': {json.dumps(out, default=str)[:200]}")]

    if name == "brain_add_conversation":
        cells: dict[str, Any] = {"Title": a["title"], "Source": a["source"]}
        for k_src, k_dst in [
            ("external_id", "External ID"),
            ("source_url", "Source URL"),
            ("started_at", "Started At"),
            ("last_message_at", "Last Message At"),
            ("message_count", "Message Count"),
            ("summary", "Summary"),
        ]:
            if k_src in a:
                cells[k_dst] = a[k_src]
        cells["Status"] = "📥 Imported"
        out = await c.add_row("conversations", cells)
        return [TextContent(type="text", text=f"OK — added conversation: {json.dumps(out, default=str)[:200]}")]

    if name == "brain_propose_dedup":
        try:
            _require_scope("ingest")
        except PermissionError as e:
            return [TextContent(type="text", text=f"Denied: {e}")]
        body = {
            "threshold": float(a.get("threshold", 0.95)),
            "limit": int(a.get("limit", 200)),
            "dry_run": True,
        }
        out = await index_call("POST", "/dedup", body)
        proposals = out.get("proposals", [])
        return [TextContent(type="text", text=(
            f"{len(proposals)} near-duplicate pairs at threshold={body['threshold']}.\n\n"
            + json.dumps(proposals[:30], indent=2, default=str)
        ))]

    if name == "brain_merge_concepts":
        try:
            _require_scope("ingest")
        except PermissionError as e:
            return [TextContent(type="text", text=f"Denied: {e}")]
        # For now we record the merge as an edit-request row in Notes (so there's
        # an AppFlowy-visible audit trail). Actual FK rewiring in the index is
        # done by a follow-up job; see runbook/merge_workflow.md.
        keep = a["keep_concept_row_id"]
        merges = a["merge_concept_row_ids"]
        reason = a.get("reason", "")
        cells = {
            "Title": f"[MERGE] keep={keep[:8]} merge={','.join(m[:8] for m in merges)}",
            "Content": (
                f"Concept merge request:\n"
                f"  KEEP:  {keep}\n"
                f"  MERGE: {merges}\n"
                f"  Reason: {reason}\n\n"
                f"Executed by: {_effective_agent()}"
            ),
            "Source": "Manual",
            "Note Type": "Reference",
            "Dedup Status": "🔗 Linked to Concept",
        }
        out = await c.add_row("notes", cells, stamp=False)
        return [TextContent(type="text", text=(
            f"Merge request logged. keep={keep} merges={merges}. "
            f"Index-side rewiring is done by the brain-index merge worker."
        ))]

    if name == "brain_propose_tag":
        cells: dict[str, Any] = {
            "Tag": a["tag"],
            "Status": "🟡 Proposed",
        }
        if "description" in a:
            cells["Description"] = a["description"]
        out = await c.add_row("tags", cells)
        return [TextContent(type="text", text=f"OK — proposed tag '{a['tag']}': {json.dumps(out, default=str)[:200]}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def _extract_row_id(out: Any) -> str:
    """AppFlowy's add-row response shape varies by version; try common spots."""
    if isinstance(out, dict):
        if "data" in out and isinstance(out["data"], dict) and "id" in out["data"]:
            return out["data"]["id"]
        if "id" in out:
            return out["id"]
    return ""


async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
