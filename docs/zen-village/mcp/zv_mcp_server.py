"""
Zen Village Brain — MCP Server
================================

Exposes the 7 self-hosted AppFlowy databases as MCP tools so Claude
(Desktop, Code, Cursor) can read and write without the UI.

Transport: stdio (default) — drop into any MCP client config.

Auth model: single service account (env ZV_MCP_USER / ZV_MCP_PASSWORD).
All agent activity flows through one AppFlowy user, audit-logged by row
`created_by` timestamps + optional `Source` field.

Environment:
  ZV_MCP_USER         (default: james.rick.stinson@gmail.com)
  ZV_MCP_PASSWORD     (required)
  ZV_APPFLOWY_BASE    (default: https://brain.zenvillagecr.com)
  ZV_WORKSPACE_ID     (required — from deploy_log.yaml)

Database IDs are discovered on startup (cached), so redeploys don't
require restarting the MCP server unless workspace changes.
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

# Per-connection agent override. stdio mode leaves this None → writes use the
# env-backed AGENT constant. HTTP mode sets this per SSE connection based on
# which bearer token was presented, so shared service account writes are
# still individually attributable.
agent_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("zv_agent", default=None)


def _effective_agent() -> str:
    return agent_ctx.get() or AGENT

log = logging.getLogger("zv-mcp")
logging.basicConfig(
    level=os.environ.get("ZV_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s zv-mcp %(message)s",
    stream=sys.stderr,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

APPFLOWY_BASE = os.environ.get("ZV_APPFLOWY_BASE", "https://brain.zenvillagecr.com")
SVC_USER = os.environ.get("ZV_MCP_USER", "james.rick.stinson@gmail.com")
SVC_PASSWORD = os.environ.get("ZV_MCP_PASSWORD")
WORKSPACE_ID = os.environ.get("ZV_WORKSPACE_ID")
AGENT = os.environ.get("ZV_MCP_AGENT", "unspecified")  # e.g. "sunheart", "atlas"

DB_SPEC = [
    ("master_list",  "01 · Master List"),
    ("weekly_log",   "02 · Weekly Log"),
    ("people",       "03 · People"),
    ("property",     "04 · Property"),
    ("decisions",    "05 · Decision Log"),
    ("events",       "06 · Events"),
    ("metrics",      "07 · Metrics"),
]
DB_NAME_BY_KEY = dict(DB_SPEC)

# ---------------------------------------------------------------------------
# AppFlowy API client (thin, async)
# ---------------------------------------------------------------------------

@dataclass
class AppFlowyClient:
    base: str
    email: str
    password: str
    workspace_id: str
    access_token: str | None = None
    refresh_token: str | None = None
    db_ids: dict[str, str] = field(default_factory=dict)     # key -> database_id
    db_views: dict[str, str] = field(default_factory=dict)   # key -> primary view_id (for deep links)
    db_fields: dict[str, dict[str, dict]] = field(default_factory=dict)  # db_key -> field_name -> field meta
    client: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient(timeout=30))

    async def login(self) -> None:
        url = f"{self.base}/gotrue/token?grant_type=password"
        r = await self.client.post(url, json={"email": self.email, "password": self.password})
        r.raise_for_status()
        j = r.json()
        self.access_token = j["access_token"]
        self.refresh_token = j["refresh_token"]
        log.info("Logged in as %s", self.email)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _req(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base}{path}"
        r = await self.client.request(method, url, headers=self._headers(), **kwargs)
        if r.status_code == 401:
            await self.login()
            r = await self.client.request(method, url, headers=self._headers(), **kwargs)
        r.raise_for_status()
        if not r.content:
            return None
        try:
            return r.json()
        except Exception:
            return r.text

    async def discover_db_ids(self) -> None:
        """
        Resolve db_key → database_id.

        AppFlowy's folder tree has a "page" for each grid (with its own
        view_id) plus children (the actual database views). We collect every
        view_id under any node whose name matches a spec entry, then
        intersect with /database's view_id → db_id map.
        """
        folder = await self._req("GET", f"/api/workspace/{self.workspace_id}/folder?depth=8")
        root = folder.get("data", folder)

        # name -> list of candidate view_ids (self + descendants)
        name_to_vids: dict[str, list[str]] = {}

        def walk(node: dict, matched_name: str | None = None) -> None:
            name = (node.get("name") or "").strip()
            current_match = matched_name
            if name in DB_NAME_BY_KEY.values():
                current_match = name
            if current_match and node.get("view_id"):
                name_to_vids.setdefault(current_match, []).append(node["view_id"])
            for c in node.get("children") or []:
                walk(c, current_match)

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
                log.warning("Could not resolve db_id for %r (candidates=%s)",
                            name, name_to_vids.get(name))
        log.info("Resolved %d/%d databases", len(self.db_ids), len(DB_SPEC))

    def db_url(self, db_key: str) -> str:
        """Clickable AppFlowy Web URL pointing at this database's primary view."""
        vid = self.db_views.get(db_key)
        if not vid:
            return self.base
        return f"{self.base}/app/{self.workspace_id}/{vid}"

    async def get_fields(self, db_key: str) -> dict[str, dict]:
        if db_key in self.db_fields:
            return self.db_fields[db_key]
        db_id = self.db_ids[db_key]
        data = await self._req("GET", f"/api/workspace/{self.workspace_id}/database/{db_id}/fields")
        fields_list = data.get("data") or data
        by_name = {f["name"]: f for f in fields_list}
        self.db_fields[db_key] = by_name
        return by_name

    async def list_rows(self, db_key: str, limit: int = 50) -> list[dict]:
        """
        Two-step fetch (this is what AppFlowy's REST forces us to do):
          1) GET /row            -> list of {id}
          2) GET /row/detail?ids= -> hydrated cells (keyed by field name)
        We apply `limit` between the two calls so we don't pull more data
        than we need.
        """
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
        # Rehydrate into [{row_id, <field_name>: <value>, ...}, ...] and
        # keep ordering from the original list call.
        by_id = {r["id"]: r for r in rows}
        out: list[dict] = []
        for rid in row_ids:
            r = by_id.get(rid, {"id": rid, "cells": {}})
            pretty: dict[str, Any] = {"row_id": r["id"]}
            for name, val in (r.get("cells") or {}).items():
                pretty[name] = _simplify_cell(val)
            out.append(pretty)
        return out

    async def add_row(self, db_key: str, cells_by_name: dict[str, Any]) -> dict:
        """
        Add a row. Every write auto-stamps the agent identity into the
        'Notes' field (or equivalent free-text field) so shared service
        account writes remain individually attributable.
        """
        db_id = self.db_ids[db_key]
        fields = await self.get_fields(db_key)

        # Auto-stamp agent+timestamp onto a free-text field if the caller
        # didn't already provide it. Prefer "Notes", fall back to "Rationale",
        # "Debrief Notes", "Summary" — first one that exists.
        stamp_targets = ["Notes", "Rationale", "Debrief Notes", "Summary"]
        who = _effective_agent()
        stamp = f"[via {who} @ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}]"
        for target in stamp_targets:
            if target in fields:
                existing = cells_by_name.get(target, "")
                cells_by_name[target] = (f"{stamp} {existing}".strip()
                                          if existing else stamp)
                break

        cells = {}
        for name, value in cells_by_name.items():
            f = fields.get(name)
            if not f:
                log.warning("Ignoring unknown field %r for %s", name, db_key)
                continue
            cells[f["id"]] = _render_cell(f, value)
        body = {"cells": cells}
        log.info("add_row db=%s agent=%s fields=%s", db_key, who, list(cells_by_name.keys()))
        return await self._req(
            "POST",
            f"/api/workspace/{self.workspace_id}/database/{db_id}/row",
            json=body,
        )


def _row_has_value(row: dict) -> bool:
    """A row is "blank" if every cell (other than row_id) is empty/null/false.
    AppFlowy creates 3 such rows every time a grid is initialized."""
    for k, v in row.items():
        if k == "row_id":
            continue
        if v in (None, "", [], {}, False):
            continue
        return True
    return False


def _simplify_cell(value: Any) -> Any:
    """
    Reshape AppFlowy's verbose cell values into something Claude can parse.

    - DateTime cells come back as {start, end, pretty_start_date, timezone, ...};
      we keep just `start` (or `pretty_start_datetime` if present).
    - Empty strings / empty arrays / None stay as-is (they're valid "no value").
    - Everything else passes through unchanged.
    """
    if isinstance(value, dict) and ("start" in value or "pretty_start_datetime" in value):
        return value.get("pretty_start_datetime") or value.get("start") or None
    return value


def _select_options(field_meta: dict) -> list[dict]:
    """Extract the option list from a SingleSelect/MultiSelect field.

    AppFlowy nests options at type_option.content.options; older/alt shapes
    also put them at type_option.options. Handle both."""
    to = field_meta.get("type_option") or {}
    # New-style: {"content": {"options": [...]}}
    content = to.get("content")
    if isinstance(content, dict) and isinstance(content.get("options"), list):
        return content["options"]
    # Alt: the content itself is a JSON string
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and isinstance(parsed.get("options"), list):
                return parsed["options"]
        except Exception:
            pass
    # Legacy shape: {"options": [...]}
    if isinstance(to.get("options"), list):
        return to["options"]
    return []


def _field_kind(field_meta: dict) -> str:
    """Normalize field-type to a canonical string name, whatever shape the
    server returns ('field_type' as string, or 'field_type_id' as int)."""
    ft = field_meta.get("field_type")
    if isinstance(ft, str):
        return ft
    fid = field_meta.get("field_type_id", ft)
    return {
        0: "RichText", 1: "Number", 2: "DateTime", 3: "SingleSelect",
        4: "MultiSelect", 5: "Checkbox", 7: "Checkbox",
    }.get(fid, "RichText")


def _render_cell(field_meta: dict, value: Any) -> Any:
    """Render a user-supplied value to AppFlowy's cell shape based on field type."""
    if value is None:
        return ""
    kind = _field_kind(field_meta)
    if kind == "RichText":
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
        opts = _select_options(field_meta)
        for o in opts:
            if str(o.get("name", "")).lower() == str(value).lower():
                return o["id"]
        log.warning("SingleSelect %r: value %r not in options %s",
                    field_meta.get("name"), value, [o.get("name") for o in opts])
        return str(value)
    if kind == "MultiSelect":
        opts = _select_options(field_meta)
        name_to_id = {str(o.get("name", "")).lower(): o["id"] for o in opts}
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",") if v.strip()]
        ids = []
        for v in value:
            sid = name_to_id.get(str(v).lower())
            if sid:
                ids.append(sid)
            else:
                log.warning("MultiSelect %r: option %r not in %s",
                            field_meta.get("name"), v, list(name_to_id))
                ids.append(str(v))
        return ",".join(ids)
    return str(value)


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server = Server("zen-village-brain")
client: AppFlowyClient | None = None


async def _ensure_ready() -> AppFlowyClient:
    global client
    if client is None:
        if not SVC_PASSWORD:
            raise RuntimeError("ZV_MCP_PASSWORD not set")
        if not WORKSPACE_ID:
            raise RuntimeError("ZV_WORKSPACE_ID not set")
        client = AppFlowyClient(
            base=APPFLOWY_BASE,
            email=SVC_USER,
            password=SVC_PASSWORD,
            workspace_id=WORKSPACE_ID,
        )
        await client.login()
        await client.discover_db_ids()
    return client


TOOLS: list[Tool] = [
    Tool(
        name="zv_status",
        description="Health check: shows which Zen Village databases are reachable and counts rows.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="zv_list",
        description=(
            "List rows from a Zen Village database with all cell values hydrated. "
            "db must be one of: master_list, weekly_log, people, property, decisions, events, metrics. "
            "By default skips blank rows left over from AppFlowy's grid defaults."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "db":    {"type": "string", "enum": [k for k, _ in DB_SPEC]},
                "limit": {"type": "integer", "default": 25, "minimum": 1, "maximum": 200},
                "include_blanks": {"type": "boolean", "default": False,
                                    "description": "If true, include rows where every meaningful cell is empty."},
            },
            "required": ["db"],
        },
    ),
    Tool(
        name="zv_get_row",
        description="Fetch a single row by its row_id from any Zen Village database (all cells hydrated).",
        inputSchema={
            "type": "object",
            "properties": {
                "db":     {"type": "string", "enum": [k for k, _ in DB_SPEC]},
                "row_id": {"type": "string"},
            },
            "required": ["db", "row_id"],
        },
    ),
    Tool(
        name="zv_search",
        description=(
            "Keyword search across a Zen Village database. Case-insensitive substring match "
            "against every text cell. Useful when you know a name or phrase but not the row_id."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "db":    {"type": "string", "enum": [k for k, _ in DB_SPEC]},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
            },
            "required": ["db", "query"],
        },
    ),
    Tool(
        name="zv_add_master_list_item",
        description="Add a row to 01 · Master List — top-of-funnel capture for any idea, task, or note.",
        inputSchema={
            "type": "object",
            "properties": {
                "title":    {"type": "string", "description": "What this item is"},
                "notes":    {"type": "string", "description": "Free-form detail"},
                "status":   {"type": "string", "description": "e.g. Inbox, In Progress, Done"},
                "priority": {"type": "string", "description": "Low|Medium|High"},
                "category": {"type": "array",  "items": {"type": "string"}, "description": "Multi-select tags"},
                "owner":    {"type": "string"},
                "due":      {"type": "string", "description": "ISO date"},
                "type":     {"type": "string", "description": "e.g. Task, Idea, Question"},
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="zv_add_weekly_log",
        description="Log the week to 02 · Weekly Log.",
        inputSchema={
            "type": "object",
            "properties": {
                "week_of":       {"type": "string", "description": "Monday of the week (YYYY-MM-DD)"},
                "week_number":   {"type": "integer"},
                "summary":       {"type": "string"},
                "stories":       {"type": "string", "description": "Stories captured this week"},
                "needs_to_know": {"type": "string", "description": "What Sunheart needs to know"},
                "next_focus":    {"type": "string", "description": "Next week's focus"},
                "litmus":        {"type": "string", "description": "Litmus score label"},
                "ops_pings":     {"type": "integer"},
                "daily_burn":    {"type": "number", "description": "Avg daily burn this week ($)"},
            },
            "required": ["week_of"],
        },
    ),
    Tool(
        name="zv_add_decision",
        description="Record a decision in 05 · Decision Log.",
        inputSchema={
            "type": "object",
            "properties": {
                "decision":  {"type": "string"},
                "rationale": {"type": "string", "description": "Why this decision was made"},
                "made_by":   {"type": "string"},
                "type":      {"type": "string"},
                "category":  {"type": "array", "items": {"type": "string"}},
                "amount":    {"type": "number"},
                "tier":      {"type": "string", "description": "Threshold Tier"},
                "outcome":   {"type": "string", "description": "After the fact outcome, if known"},
            },
            "required": ["decision"],
        },
    ),
    Tool(
        name="zv_add_person",
        description=(
            "Add a row to 03 · People — ground team, prospects, partners, venues. "
            "For UPDATES to existing people (e.g. flipping someone's Role, Trust Level, or Status), "
            "do NOT use this tool — use zv_propose_change instead, because AppFlowy's REST API "
            "does not expose row updates (only the desktop/web UI can edit rows in place)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name":         {"type": "string"},
                "type":         {"type": "string", "description": "e.g. Ground Team, Prospect, Partner, Venue, Vendor"},
                "role":         {"type": "array", "items": {"type": "string"}, "description": "Multi-select roles"},
                "trust_level":  {"type": "string", "description": "Core|Trusted|Trial"},
                "status":       {"type": "string", "description": "Active|Paused|Archived"},
                "next_action":  {"type": "string"},
                "contact":      {"type": "string"},
                "notes":        {"type": "string"},
                "linked_event": {"type": "string", "description": "Event name this person is connected to"},
                "first_contact":{"type": "string", "description": "ISO date"},
                "last_touch":   {"type": "string", "description": "ISO date"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="zv_add_property",
        description="Add a row to 04 · Property — houses, lands, venues under Zen Village's orbit.",
        inputSchema={
            "type": "object",
            "properties": {
                "name":        {"type": "string"},
                "status":      {"type": "string"},
                "type":        {"type": "string"},
                "location":    {"type": "string"},
                "contact":     {"type": "string"},
                "monthly_cost":{"type": "number"},
                "capacity":    {"type": "integer"},
                "notes":       {"type": "string"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="zv_add_metric",
        description="Add a row to 07 · Metrics — weekly/monthly scoreboard entries.",
        inputSchema={
            "type": "object",
            "properties": {
                "metric":       {"type": "string", "description": "Metric name (e.g. Weekly Revenue)"},
                "period":       {"type": "string", "description": "e.g. 2026-W17, 2026-04, 2026-Q2"},
                "value":        {"type": "number"},
                "target":       {"type": "number"},
                "unit":         {"type": "string"},
                "notes":        {"type": "string"},
            },
            "required": ["metric"],
        },
    ),
    Tool(
        name="zv_propose_change",
        description=(
            "Record a requested UPDATE to an existing row. "
            "Use this whenever the user wants to change a field on a person, property, event, "
            "or any other existing record — because AppFlowy's REST API does not expose row "
            "updates, only row creation. This tool files a structured task in the Master List "
            "that a human (or future automation) can execute in the AppFlowy UI. "
            "Always cite the target row's Name/Title and row_id if known."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "db":           {"type": "string", "enum": [k for k, _ in DB_SPEC],
                                  "description": "Which database the target row lives in"},
                "target_name":  {"type": "string", "description": "Human-readable target (e.g. 'Elizabeth', 'Casa Retreat')"},
                "target_row_id":{"type": "string", "description": "Optional row_id for unambiguous reference"},
                "changes":      {"type": "object", "description": "Field→new_value map (e.g. {\"Trust Level\": \"Core\", \"Role\": [\"Advisor\"]})"},
                "reason":       {"type": "string", "description": "Why this change is needed"},
                "urgency":      {"type": "string", "description": "Low|Medium|High"},
            },
            "required": ["db", "target_name", "changes"],
        },
    ),
    Tool(
        name="zv_add_event",
        description="Create a row in 06 · Events (retreat, gathering, ceremony, offsite).",
        inputSchema={
            "type": "object",
            "properties": {
                "event_name":       {"type": "string"},
                "date":             {"type": "string"},
                "type":             {"type": "string"},
                "tier":             {"type": "string"},
                "status":           {"type": "string"},
                "attendees_expected": {"type": "integer"},
                "attendees_actual": {"type": "integer"},
                "revenue":          {"type": "number"},
                "costs":            {"type": "number"},
                "luma_link":        {"type": "string"},
                "debrief_notes":    {"type": "string"},
                "lessons":          {"type": "string"},
            },
            "required": ["event_name"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    c = await _ensure_ready()
    arguments = arguments or {}

    if name == "zv_status":
        lines = [f"AppFlowy base:   {APPFLOWY_BASE}", f"Service account: {SVC_USER}", ""]
        for key, full_name in DB_SPEC:
            if key in c.db_ids:
                try:
                    rows = await c.list_rows(key, limit=200)
                    lines.append(f"  {full_name:22s} → {len(rows)} rows")
                except Exception as e:
                    lines.append(f"  {full_name:22s} → ERROR {e}")
            else:
                lines.append(f"  {full_name:22s} → (not resolved)")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "zv_list":
        db = arguments["db"]
        limit = int(arguments.get("limit", 25))
        include_blanks = bool(arguments.get("include_blanks", False))
        # Fetch more than `limit` so we can filter blanks and still return `limit` non-blanks.
        fetch = limit if include_blanks else min(limit * 3 + 10, 200)
        rows = await c.list_rows(db, limit=fetch)
        if not include_blanks:
            rows = [r for r in rows if _row_has_value(r)]
        rows = rows[:limit]
        return [TextContent(type="text", text=json.dumps(rows, indent=2, default=str))]

    if name == "zv_get_row":
        db = arguments["db"]
        rid = arguments["row_id"]
        db_id = c.db_ids[db]
        detail = await c._req(
            "GET",
            f"/api/workspace/{c.workspace_id}/database/{db_id}/row/detail",
            params={"ids": rid},
        )
        rows = (detail.get("data") if isinstance(detail, dict) else detail) or []
        if not rows:
            return [TextContent(type="text", text=f"No row found with id {rid} in {db}")]
        r = rows[0]
        pretty = {"row_id": r["id"]}
        for n, v in (r.get("cells") or {}).items():
            pretty[n] = _simplify_cell(v)
        return [TextContent(type="text", text=json.dumps(pretty, indent=2, default=str))]

    if name == "zv_search":
        db = arguments["db"]
        q = arguments["query"].lower()
        limit = int(arguments.get("limit", 20))
        # Pull up to 200 rows and filter locally — fine for the brain's current scale.
        rows = await c.list_rows(db, limit=200)
        def matches(r: dict) -> bool:
            for v in r.values():
                if isinstance(v, str) and q in v.lower():
                    return True
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and q in item.lower():
                            return True
            return False
        hits = [r for r in rows if matches(r)][:limit]
        return [TextContent(type="text", text=json.dumps(hits, indent=2, default=str))]

    if name == "zv_propose_change":
        db      = arguments["db"]
        target  = arguments["target_name"]
        row_id  = arguments.get("target_row_id")
        changes = arguments["changes"]
        reason  = arguments.get("reason", "")
        urgency = arguments.get("urgency", "Medium")
        deep_link = c.db_url(db)
        change_lines = [f"  • {k}: {json.dumps(v) if not isinstance(v, str) else v}" for k, v in changes.items()]
        # Title prefix doubles as our filter token for the Pending Edits view.
        title = f"[Edit Request] {DB_NAME_BY_KEY.get(db, db)}: {target}"
        notes = (
            f"Open: {deep_link}\n\n"
            f"Target DB:   {db}\n"
            f"Target name: {target}\n"
            + (f"Target row_id: {row_id}\n" if row_id else "")
            + "Changes:\n" + "\n".join(change_lines)
            + (f"\nReason: {reason}" if reason else "")
            + "\n\nHow to execute:\n"
              f"  1. Click the link above → opens the {DB_NAME_BY_KEY.get(db, db)} grid\n"
              f"  2. Find '{target}' (Cmd/Ctrl-F helps)\n"
              f"  3. Apply the field changes above\n"
              f"  4. Come back to this Master List row, set Status → 🟢 Done"
        )
        # Map urgency → the actual Priority options in the workspace
        priority = {"High": "P0", "Medium": "P1", "Low": "P2"}.get(urgency, "P1")
        cells = _title_cell("Title", title)
        cells["Notes"]    = notes
        cells["Status"]   = "🔵 Proposed"
        cells["Priority"] = priority
        cells["Category"] = ["Admin"]
        out = await c.add_row("master_list", cells)
        return [TextContent(type="text", text=(
            f"Logged an edit request in the Master List (AppFlowy's REST API doesn't "
            f"support row edits, so this is the right pattern).\n\n"
            f"Title: {title}\nPriority: {priority} ({urgency})\nOpen: {deep_link}\n\n"
            f"Changes proposed:\n" + "\n".join(change_lines) +
            f"\n\nrow: {json.dumps(out, default=str)[:200]}"
        ))]

    # Write tools map to column names from the schema.
    mapping = {
        "zv_add_master_list_item": ("master_list", _build_master_list_cells),
        "zv_add_weekly_log":       ("weekly_log",  _build_weekly_log_cells),
        "zv_add_decision":         ("decisions",   _build_decision_cells),
        "zv_add_event":            ("events",      _build_event_cells),
        "zv_add_person":           ("people",      _build_person_cells),
        "zv_add_property":         ("property",    _build_property_cells),
        "zv_add_metric":           ("metrics",     _build_metric_cells),
    }
    if name in mapping:
        db, builder = mapping[name]
        cells = builder(arguments)
        out = await c.add_row(db, cells)
        return [TextContent(type="text", text=f"OK — added to {DB_NAME_BY_KEY[db]}:\n{json.dumps(out, indent=2, default=str)}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


# ---------------------------------------------------------------------------
# Argument → AppFlowy cell mappers
# Field names follow zv_schema.json exactly.
# If a DB's primary column is still named "Name" (from AppFlowy defaults),
# we try both the spec name and "Name" so the MCP works pre- and post-cleanup.
# ---------------------------------------------------------------------------

def _title_cell(primary_name: str, value: str) -> dict:
    """Set the named column AND the default 'Name' column so writes work
    whether or not the primary column has been renamed from the AppFlowy
    default to the spec name."""
    return {primary_name: value, "Name": value}


def _build_master_list_cells(a: dict) -> dict:
    c = _title_cell("Title", a["title"])
    if "notes"    in a: c["Notes"]    = a["notes"]
    if "status"   in a: c["Status"]   = a["status"]
    if "priority" in a: c["Priority"] = a["priority"]
    if "category" in a: c["Category"] = a["category"]
    if "owner"    in a: c["Owner"]    = a["owner"]
    if "due"      in a: c["Due"]      = a["due"]
    if "type"     in a: c["Type"]     = a["type"]
    return c


def _build_weekly_log_cells(a: dict) -> dict:
    c = _title_cell("Week Of", a["week_of"])
    if "week_number"   in a: c["Week Number"]   = a["week_number"]
    if "summary"       in a: c["Summary"]       = a["summary"]
    if "stories"       in a: c["Stories Captured"] = a["stories"]
    if "needs_to_know" in a: c["What Sunheart Needs to Know"] = a["needs_to_know"]
    if "next_focus"    in a: c["Next Week's Focus"] = a["next_focus"]
    if "litmus"        in a: c["Litmus Score"]  = a["litmus"]
    if "ops_pings"     in a: c["Ops Pings Count"] = a["ops_pings"]
    if "daily_burn"    in a: c["Daily Burn Avg"] = a["daily_burn"]
    return c


def _build_decision_cells(a: dict) -> dict:
    c = _title_cell("Decision", a["decision"])
    if "rationale" in a: c["Rationale"] = a["rationale"]
    if "made_by"   in a: c["Made By"]   = a["made_by"]
    if "type"      in a: c["Type"]      = a["type"]
    if "category"  in a: c["Category"]  = a["category"]
    if "amount"    in a: c["Amount"]    = a["amount"]
    if "tier"      in a: c["Threshold Tier"] = a["tier"]
    if "outcome"   in a: c["Outcome"]   = a["outcome"]
    return c


def _build_person_cells(a: dict) -> dict:
    c = _title_cell("Name", a["name"])
    if "type"          in a: c["Type"]         = a["type"]
    if "role"          in a: c["Role"]         = a["role"]
    if "trust_level"   in a: c["Trust Level"]  = a["trust_level"]
    if "status"        in a: c["Status"]       = a["status"]
    if "next_action"   in a: c["Next Action"]  = a["next_action"]
    if "contact"       in a: c["Contact"]      = a["contact"]
    if "notes"         in a: c["Notes"]        = a["notes"]
    if "linked_event"  in a: c["Linked to Event"] = a["linked_event"]
    if "first_contact" in a: c["First Contact"] = a["first_contact"]
    if "last_touch"    in a: c["Last Touch"]   = a["last_touch"]
    return c


def _build_property_cells(a: dict) -> dict:
    c = _title_cell("Name", a["name"])
    if "status"       in a: c["Status"]       = a["status"]
    if "type"         in a: c["Type"]         = a["type"]
    if "location"     in a: c["Location"]     = a["location"]
    if "contact"      in a: c["Contact"]      = a["contact"]
    if "monthly_cost" in a: c["Monthly Cost"] = a["monthly_cost"]
    if "capacity"     in a: c["Capacity"]     = a["capacity"]
    if "notes"        in a: c["Notes"]        = a["notes"]
    return c


def _build_metric_cells(a: dict) -> dict:
    c = _title_cell("Metric", a["metric"])
    if "period" in a: c["Period"] = a["period"]
    if "value"  in a: c["Value"]  = a["value"]
    if "target" in a: c["Target"] = a["target"]
    if "unit"   in a: c["Unit"]   = a["unit"]
    if "notes"  in a: c["Notes"]  = a["notes"]
    return c


def _build_event_cells(a: dict) -> dict:
    c = _title_cell("Event Name", a["event_name"])
    if "date"   in a: c["Date"]   = a["date"]
    if "type"   in a: c["Type"]   = a["type"]
    if "tier"   in a: c["Tier"]   = a["tier"]
    if "status" in a: c["Status"] = a["status"]
    if "attendees_expected" in a: c["Attendees Expected"] = a["attendees_expected"]
    if "attendees_actual"   in a: c["Attendees Actual"]   = a["attendees_actual"]
    if "revenue" in a: c["Revenue"] = a["revenue"]
    if "costs"   in a: c["Costs"]   = a["costs"]
    if "luma_link" in a: c["Luma Link"] = a["luma_link"]
    if "debrief_notes" in a: c["Debrief Notes"] = a["debrief_notes"]
    if "lessons" in a: c["Lessons Learned"] = a["lessons"]
    return c


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
