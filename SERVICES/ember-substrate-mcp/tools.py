"""
ember-substrate-mcp · tools.py
==============================

15 read tools + 5 write tools.

Design rules:
- All HTTP calls share `_get_substrate(path, method, body)` (bearer auth,
  X-Client header).
- Every write tool runs `permissions.check_write(target)` BEFORE any open
  or HTTP POST. On 403 the tool returns the structured error directly.
- Every successful write tool fires `ember_log_event` with
  type=`mcp_write_attempt` (best-effort, failure is logged not raised).
- NO subprocess. NO Task. NO agent dispatch.
- Filenames + slugs validated kebab-case.
- All paths anchored to FPAI_COCKPIT_ROOT / EMBER_MEMORY_GLOBAL /
  EMBER_FPAI_CONFIG; `..` is rejected.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from mcp.types import TextContent, Tool

from permissions import (
    EMBER_FPAI_CONFIG,
    EMBER_MEMORY_GLOBAL,
    FPAI_COCKPIT_ROOT,
    check_write,
    is_kebab_filename,
    is_kebab_slug,
)

log = logging.getLogger("ember-mcp.tools")

# ---------------------------------------------------------------------------
# Env + token
# ---------------------------------------------------------------------------

EMBER_API_BASE = os.environ.get("EMBER_API_BASE", "http://127.0.0.1:8765").rstrip("/")
EMBER_API_TOKEN_FILE = os.environ.get(
    "EMBER_API_TOKEN_FILE", "/Users/jamessunheart/.config/fpai/api.token"
)
MCP_CLIENT_HEADER = os.environ.get("EMBER_MCP_CLIENT", "claude-desktop-mcp")


def _load_token() -> str:
    p = Path(EMBER_API_TOKEN_FILE).expanduser()
    if not p.exists():
        raise RuntimeError(
            f"EMBER_API_TOKEN_FILE not found: {p}. Refusing to start without bearer."
        )
    tok = p.read_text(encoding="utf-8").strip()
    if not tok:
        raise RuntimeError(f"EMBER_API_TOKEN_FILE is empty: {p}")
    return tok


_TOKEN: Optional[str] = None


def _token() -> str:
    global _TOKEN
    if _TOKEN is None:
        _TOKEN = _load_token()
    return _TOKEN


# ---------------------------------------------------------------------------
# Substrate HTTP helper
# ---------------------------------------------------------------------------


async def _get_substrate(
    path: str,
    method: str = "GET",
    body: Optional[dict] = None,
    timeout: float = 15.0,
) -> Any:
    """Bearer-auth call to the FastAPI substrate. Returns parsed JSON (or text)."""
    url = f"{EMBER_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {_token()}",
        "X-Client": MCP_CLIENT_HEADER,
    }
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.request(method, url, headers=headers, json=body)
        r.raise_for_status()
        if not r.content:
            return None
        ct = r.headers.get("content-type", "")
        if "application/json" in ct:
            return r.json()
        return r.text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _json(obj: Any) -> list[TextContent]:
    return _ok(json.dumps(obj, indent=2, default=str, ensure_ascii=False))


def _err(reason: str, **extra: Any) -> list[TextContent]:
    payload = {"error": reason, **extra}
    return _ok(json.dumps(payload, indent=2, default=str, ensure_ascii=False))


def _resolve_repo(rel: str) -> Path:
    """Resolve a repo-relative read path. Reject `..` / absolute escape."""
    if rel.startswith("/") or ".." in Path(rel).parts:
        raise ValueError(f"unsafe path: {rel!r}")
    p = (FPAI_COCKPIT_ROOT / rel).resolve()
    # Must remain inside cockpit
    try:
        p.relative_to(FPAI_COCKPIT_ROOT)
    except ValueError as e:
        raise ValueError(f"path escapes cockpit: {rel!r}") from e
    return p


def _resolve_memory(rel: str) -> Path:
    if rel.startswith("/") or ".." in Path(rel).parts:
        raise ValueError(f"unsafe path: {rel!r}")
    p = (EMBER_MEMORY_GLOBAL / rel).resolve()
    try:
        p.relative_to(EMBER_MEMORY_GLOBAL)
    except ValueError as e:
        raise ValueError(f"path escapes memory-global: {rel!r}") from e
    return p


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return json.dumps({"present": False, "path": str(path)})
    except Exception as e:
        return json.dumps({"error": "read_failed", "path": str(path), "detail": str(e)})


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


async def _audit_write(target: str, tool: str, meta: Optional[dict] = None) -> None:
    """Fire mcp_write_attempt event. Best-effort — log on failure, do NOT raise."""
    payload: dict[str, Any] = {
        "tool": tool,
        "target": target,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if meta:
        payload["meta"] = meta
    body = {
        "type": "mcp_write_attempt",
        "actor": MCP_CLIENT_HEADER,
        "payload": payload,
    }
    try:
        await _get_substrate("/event", method="POST", body=body, timeout=5.0)
    except Exception as e:
        log.warning("audit event failed for tool=%s target=%s: %s", tool, target, e)


# ---------------------------------------------------------------------------
# TOOL DEFINITIONS
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    # ---------------- READ (15) ----------------
    Tool(
        name="ember_read_state",
        description="Read substrate state via GET /state or /state/{layer}. Layer is one of: identity, state, memory, skill, interface (or omit for full).",
        inputSchema={
            "type": "object",
            "properties": {
                "layer": {"type": "string", "description": "Optional layer name."},
            },
        },
    ),
    Tool(
        name="ember_read_now",
        description="Read core/STATE/NOW.md — the founder-priorities surface.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ember_read_goals",
        description="Read core/STATE/AI_GOALS.md — the AI working goals + handoff notes.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ember_read_scene",
        description="Read core/STATE/SCENE.md — the total-scene snapshot (location · body · social · tooling).",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ember_read_alignment",
        description="Read ~/.claude/memory-global/identity/ALIGNMENT.md — INTENT · TOP 3 · BLOCKERS · NEXT MOVE.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ember_read_story_handoff",
        description="Read the 'Last session handoff' section of ~/.claude/memory-global/identity/STORY.md.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ember_read_next_turn_surface",
        description="Read ~/.config/fpai/specs/next-turn-surface.md if present; otherwise returns {present:false}.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ember_read_narrator_log",
        description="Read core/INTELLIGENCE/narrator/sessions/<date>.md (date in YYYY-MM-DD). Omit date for today.",
        inputSchema={
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD; defaults to today UTC."},
            },
        },
    ),
    Tool(
        name="ember_read_events",
        description="Tail events.jsonl. Filter by since_minutes (default 60) and types (optional list).",
        inputSchema={
            "type": "object",
            "properties": {
                "since_minutes": {"type": "integer", "default": 60, "minimum": 1, "maximum": 10080},
                "types": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 200, "minimum": 1, "maximum": 2000},
            },
        },
    ),
    Tool(
        name="ember_read_decisions",
        description="Tail decisions.jsonl. Filter by since_days (default 30).",
        inputSchema={
            "type": "object",
            "properties": {
                "since_days": {"type": "integer", "default": 30, "minimum": 1, "maximum": 365},
                "limit": {"type": "integer", "default": 200, "minimum": 1, "maximum": 2000},
            },
        },
    ),
    Tool(
        name="ember_read_memory_search",
        description="Case-insensitive substring grep across ~/.claude/memory-global/*.md. Returns matched files + first matching line.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="ember_read_agent",
        description="Read .claude/agents/<name>.md. `name` must be a single kebab-case slug — refuses `/` or `..`.",
        inputSchema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    ),
    Tool(
        name="ember_list_agents",
        description="List .claude/agents/*.md with first-line description.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="ember_read_agent_identity",
        description="Read ~/.claude/memory-global/agent_identity/<agent>/*.md if shipped; otherwise {shipped:false}.",
        inputSchema={
            "type": "object",
            "properties": {"agent": {"type": "string"}},
            "required": ["agent"],
        },
    ),
    Tool(
        name="ember_read_mindmap",
        description="Read core/STATE/MINDMAP.md.",
        inputSchema={"type": "object", "properties": {}},
    ),
    # ---------------- WRITE (5) ----------------
    Tool(
        name="ember_log_message",
        description="POST /message — append a message to Ember's inbox (human-reviewed). Source defaults to claude-desktop.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "source": {"type": "string", "default": "claude-desktop"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"], "default": "normal"},
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="ember_log_event",
        description="POST /event — append a structured event with actor=claude-desktop-mcp.",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "payload": {"type": "object"},
            },
            "required": ["type"],
        },
    ),
    Tool(
        name="ember_queue_forge_work_order",
        description="Write a Forge work-order to ~/.config/fpai/forge/queued/<UTC>_<slug>.md. Slug is kebab-case.",
        inputSchema={
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "content": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"], "default": "normal"},
            },
            "required": ["slug", "content"],
        },
    ),
    Tool(
        name="ember_queue_canonization",
        description="Append a canonization proposal to ~/.config/fpai/standards/canonize_queue.md.",
        inputSchema={
            "type": "object",
            "properties": {
                "discipline_name": {"type": "string"},
                "reason": {"type": "string"},
                "proposed_mechanism": {"type": "string"},
            },
            "required": ["discipline_name", "reason", "proposed_mechanism"],
        },
    ),
    Tool(
        name="ember_save_memory",
        description="Write a NEW memory file at ~/.claude/memory-global/<filename>.md. Filename must be kebab-case; refuses identity/* and overwrite of existing files.",
        inputSchema={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "e.g. 'project_thing.md'"},
                "content": {"type": "string"},
            },
            "required": ["filename", "content"],
        },
    ),
]


# ---------------------------------------------------------------------------
# DISPATCHER
# ---------------------------------------------------------------------------


async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    a = arguments or {}

    # ============= READ =============

    if name == "ember_read_state":
        layer = a.get("layer")
        path = f"/state/{layer}" if layer else "/state"
        data = await _get_substrate(path)
        return _json(data)

    if name == "ember_read_now":
        return _ok(_read_text(_resolve_repo("core/STATE/NOW.md")))

    if name == "ember_read_goals":
        return _ok(_read_text(_resolve_repo("core/STATE/AI_GOALS.md")))

    if name == "ember_read_scene":
        return _ok(_read_text(_resolve_repo("core/STATE/SCENE.md")))

    if name == "ember_read_alignment":
        return _ok(_read_text(_resolve_memory("identity/ALIGNMENT.md")))

    if name == "ember_read_story_handoff":
        text = _read_text(_resolve_memory("identity/STORY.md"))
        # Extract the "Last session handoff" section if present.
        m = re.search(
            r"(?:^|\n)(#+\s*Last session handoff.*?)(?=\n#+\s|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            return _ok(m.group(1).strip())
        return _ok(text)

    if name == "ember_read_next_turn_surface":
        p = (EMBER_FPAI_CONFIG / "specs" / "next-turn-surface.md").resolve()
        if not p.exists():
            return _json({"present": False, "path": str(p)})
        return _ok(p.read_text(encoding="utf-8"))

    if name == "ember_read_narrator_log":
        date = a.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            return _err("invalid_date", expected="YYYY-MM-DD", got=date)
        return _ok(_read_text(_resolve_repo(f"core/INTELLIGENCE/narrator/sessions/{date}.md")))

    if name == "ember_read_events":
        since_minutes = int(a.get("since_minutes", 60))
        types = a.get("types") or None
        limit = int(a.get("limit", 200))
        events_path = EMBER_FPAI_CONFIG / "ember" / "state" / "events.jsonl"
        return _json(_tail_jsonl(events_path, since_seconds=since_minutes * 60, types=types, limit=limit))

    if name == "ember_read_decisions":
        since_days = int(a.get("since_days", 30))
        limit = int(a.get("limit", 200))
        decisions_path = EMBER_FPAI_CONFIG / "ember" / "state" / "decisions.jsonl"
        return _json(_tail_jsonl(decisions_path, since_seconds=since_days * 86400, types=None, limit=limit))

    if name == "ember_read_memory_search":
        q = a["query"].lower()
        limit = int(a.get("limit", 5))
        hits: list[dict] = []
        try:
            for path in sorted(EMBER_MEMORY_GLOBAL.glob("*.md")):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if q in line.lower():
                        hits.append({"file": path.name, "line": i, "text": line.strip()[:240]})
                        break
                if len(hits) >= limit:
                    break
        except Exception as e:
            return _err("search_failed", detail=str(e))
        return _json({"query": a["query"], "hits": hits})

    if name == "ember_read_agent":
        agent_name = a["name"]
        if not is_kebab_slug(agent_name):
            return _err("invalid_agent_name", expected="kebab-case slug", got=agent_name)
        return _ok(_read_text(_resolve_repo(f".claude/agents/{agent_name}.md")))

    if name == "ember_list_agents":
        agents_dir = (FPAI_COCKPIT_ROOT / ".claude" / "agents").resolve()
        out: list[dict] = []
        try:
            for p in sorted(agents_dir.glob("*.md")):
                first = ""
                try:
                    with p.open("r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            stripped = line.strip()
                            if stripped:
                                first = stripped[:240]
                                break
                except Exception:
                    pass
                out.append({"name": p.stem, "first_line": first})
        except Exception as e:
            return _err("list_failed", detail=str(e))
        return _json(out)

    if name == "ember_read_agent_identity":
        agent = a["agent"]
        if not is_kebab_slug(agent):
            return _err("invalid_agent_name", expected="kebab-case slug", got=agent)
        agent_dir = (EMBER_MEMORY_GLOBAL / "agent_identity" / agent).resolve()
        try:
            agent_dir.relative_to(EMBER_MEMORY_GLOBAL)
        except ValueError:
            return _err("path_escapes_memory_global", agent=agent)
        if not agent_dir.exists():
            return _json({"shipped": False, "agent": agent, "dir": str(agent_dir)})
        files: dict[str, str] = {}
        for p in sorted(agent_dir.glob("*.md")):
            files[p.name] = p.read_text(encoding="utf-8", errors="replace")
        return _json({"shipped": True, "agent": agent, "files": files})

    if name == "ember_read_mindmap":
        return _ok(_read_text(_resolve_repo("core/STATE/MINDMAP.md")))

    # ============= WRITE =============

    if name == "ember_log_message":
        text = a["text"]
        body = {
            # Substrate's MessageIn schema: body (str) · from_client (str?) · priority (str)
            "body": text,
            "from_client": a.get("source", "claude-desktop"),
            "priority": a.get("priority", "normal"),
        }
        # Substrate writes the message; we do NOT check_write a filesystem path
        # because /message routes through the bearer-protected FastAPI.
        try:
            data = await _get_substrate("/message", method="POST", body=body)
            await _audit_write(target="/message", tool=name, meta={"source": body["from_client"], "priority": body["priority"]})
            return _json({"ok": True, "result": data})
        except httpx.HTTPStatusError as e:
            return _err("substrate_http_error", status=e.response.status_code, detail=e.response.text[:240])
        except Exception as e:
            return _err("substrate_call_failed", detail=str(e))

    if name == "ember_log_event":
        evt_type = a["type"]
        payload = dict(a.get("payload") or {})
        payload.setdefault("at", datetime.now(timezone.utc).isoformat())
        body = {
            "type": evt_type,
            "actor": MCP_CLIENT_HEADER,
            "payload": payload,
        }
        try:
            data = await _get_substrate("/event", method="POST", body=body)
            # NOTE: do not _audit_write here — it would recurse on every event.
            return _json({"ok": True, "result": data})
        except httpx.HTTPStatusError as e:
            return _err("substrate_http_error", status=e.response.status_code, detail=e.response.text[:240])
        except Exception as e:
            return _err("substrate_call_failed", detail=str(e))

    if name == "ember_queue_forge_work_order":
        slug = a["slug"]
        content = a["content"]
        priority = a.get("priority", "normal")
        if not is_kebab_slug(slug):
            return _err("invalid_slug", expected="kebab-case", got=slug)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{ts}_{slug}.md"
        target = (EMBER_FPAI_CONFIG / "forge" / "queued" / filename).resolve()
        deny = check_write(target)
        if deny is not None:
            return _json(deny)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            header = (
                f"---\nqueued_at: {datetime.now(timezone.utc).isoformat()}\n"
                f"slug: {slug}\npriority: {priority}\n"
                f"queued_by: {MCP_CLIENT_HEADER}\n---\n\n"
            )
            target.write_text(header + content, encoding="utf-8")
            await _audit_write(target=str(target), tool=name, meta={"slug": slug, "priority": priority, "bytes": len(content)})
            return _json({"ok": True, "path": str(target)})
        except Exception as e:
            return _err("write_failed", detail=str(e))

    if name == "ember_queue_canonization":
        target = (EMBER_FPAI_CONFIG / "standards" / "canonize_queue.md").resolve()
        deny = check_write(target)
        if deny is not None:
            return _json(deny)
        entry = (
            f"\n## {datetime.now(timezone.utc).isoformat()} · {a['discipline_name']}\n\n"
            f"- **reason:** {a['reason']}\n"
            f"- **proposed_mechanism:** {a['proposed_mechanism']}\n"
            f"- **queued_by:** {MCP_CLIENT_HEADER}\n"
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as f:
                f.write(entry)
            await _audit_write(target=str(target), tool=name, meta={"discipline_name": a["discipline_name"]})
            return _json({"ok": True, "path": str(target), "appended_bytes": len(entry)})
        except Exception as e:
            return _err("write_failed", detail=str(e))

    if name == "ember_save_memory":
        filename = a["filename"]
        content = a["content"]
        if not is_kebab_filename(filename):
            return _err("invalid_filename", expected="kebab-case + .md", got=filename)
        target = (EMBER_MEMORY_GLOBAL / filename).resolve()
        # check_write enforces identity/* refusal + roots
        deny = check_write(target)
        if deny is not None:
            return _json(deny)
        # No-overwrite policy
        if target.exists():
            return _err("would_overwrite", path=str(target))
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            await _audit_write(target=str(target), tool=name, meta={"filename": filename, "bytes": len(content)})
            return _json({"ok": True, "path": str(target)})
        except Exception as e:
            return _err("write_failed", detail=str(e))

    return _err("unknown_tool", name=name)


# ---------------------------------------------------------------------------
# jsonl tail helper
# ---------------------------------------------------------------------------


def _tail_jsonl(
    path: Path,
    since_seconds: int,
    types: Optional[list[str]],
    limit: int,
) -> dict:
    if not path.exists():
        return {"present": False, "path": str(path), "items": []}
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - since_seconds
    items: list[dict] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if types and rec.get("type") not in types:
                    continue
                # Parse `at` if present
                at_str = rec.get("at") or rec.get("ts") or rec.get("timestamp")
                if at_str:
                    try:
                        ts = datetime.fromisoformat(at_str.replace("Z", "+00:00")).timestamp()
                        if ts < cutoff:
                            continue
                    except Exception:
                        pass
                items.append(rec)
    except Exception as e:
        return {"present": True, "path": str(path), "error": str(e), "items": []}
    return {"present": True, "path": str(path), "count": len(items), "items": items[-limit:]}
