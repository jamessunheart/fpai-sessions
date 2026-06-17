"""Bounded build-context injector for owner chat.

The context is advisory only: it pins the current buildstream state into each
chat prompt, but it does not let the bot route, write, deploy, spend, or decide.
It is reversible with SH_BUILD_CONTEXT_DISABLE=1 and bounded by row/char limits.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[3]))
DEFAULT_MAX_ITEMS = int(os.environ.get("SH_BUILD_CONTEXT_MAX_ITEMS", "6"))
DEFAULT_MAX_CHARS = int(os.environ.get("SH_BUILD_CONTEXT_MAX_CHARS", "1800"))
DEFAULT_DIAGNOSTIC_CONTEXT_FILE = Path(
    os.environ.get("SELF_DIAGNOSTIC_CONTEXT_FILE", "/opt/fpai-build/.self_diagnostic_context.json")
)
SUPABASE_TIMEOUT_SECONDS = float(os.environ.get("SH_BUILD_CONTEXT_TIMEOUT_SECONDS", "2.0"))


@dataclass(frozen=True)
class BuildContext:
    source: str
    focus: list[str]
    active_loops: list[str]
    open_intents: list[str]
    system_status: list[str] | None = None
    corrections: list[str] | None = None

    def is_empty(self) -> bool:
        return not (
            self.focus
            or self.active_loops
            or self.open_intents
            or self.system_status
            or self.corrections
        )


async def build_context_system_suffix(
    *,
    repo_root: Path | str = REPO_ROOT,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_chars: int = DEFAULT_MAX_CHARS,
    conversation_id: str | None = None,
) -> str:
    """Return a system-prompt suffix. Empty string means no injection."""
    if os.environ.get("SH_BUILD_CONTEXT_DISABLE", "").strip() == "1":
        return ""
    context = await load_build_context(
        repo_root=Path(repo_root),
        max_items=max_items,
        conversation_id=conversation_id,
    )
    diagnostic = render_active_diagnostic_context(max_chars=max_chars)
    becoming = await _render_becoming_context(conversation_id=conversation_id, max_chars=max_chars)
    parts: list[str] = []
    if not context.is_empty():
        parts.append(render_build_context(context, max_chars=max_chars))
    if becoming:
        parts.append(becoming)
    suffix = "\n\n".join(parts)
    if diagnostic:
        suffix = diagnostic + ("\n\n" + suffix if suffix else "")
    return "\n\n" + suffix if suffix else ""


def diagnostic_system_prefix(path: Path | str = DEFAULT_DIAGNOSTIC_CONTEXT_FILE) -> str:
    """Return the short-lived diagnostic interview instruction, if active."""
    context = load_active_diagnostic_context(Path(path))
    if not context:
        return ""
    prefix = str(context.get("prompt_prefix") or "").strip()
    return prefix + "\n\n" if prefix else ""


def render_active_diagnostic_context(
    *,
    path: Path | str = DEFAULT_DIAGNOSTIC_CONTEXT_FILE,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    context = load_active_diagnostic_context(Path(path))
    if not context:
        return ""
    lines = [
        "--- ACTIVE COUNCIL SELF-DIAGNOSTIC CONTEXT ---",
        f"Audit: {context.get('audit_id', '')}",
        "Use this context to answer the council's diagnostic questions honestly from your recent operating experience.",
    ]
    recent = context.get("last_50_tg_messages") or []
    if recent:
        lines.append("Recent Telegram turns:")
        for item in recent[:12]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('role', '?')}: {_clip_markdown(str(item.get('text') or ''))}")
    not_now = context.get("not_now_decisions") or []
    if not_now:
        lines.append("Decisions James answered not now:")
        for item in not_now[:8]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('id', '')}: {_clip_markdown(str(item.get('question') or ''))}")
    rejected = context.get("rejected_builds") or []
    if rejected:
        lines.append("Rejected builds:")
        for item in rejected[:8]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('id', '')}: {_clip_markdown(str(item.get('notes') or item.get('branch') or ''))}")
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


def load_active_diagnostic_context(path: Path = DEFAULT_DIAGNOSTIC_CONTEXT_FILE) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    expires_at = _parse_time(str(data.get("expires_at") or ""))
    if expires_at and expires_at < datetime.now(timezone.utc):
        return None
    return data


def _parse_time(value: str) -> datetime | None:
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def load_build_context(
    *,
    repo_root: Path,
    max_items: int = DEFAULT_MAX_ITEMS,
    conversation_id: str | None = None,
) -> BuildContext:
    """Prefer Supabase when configured; otherwise use repo-local mirrors."""
    supabase = await _load_supabase_context(max_items=max_items)
    context: BuildContext
    if supabase and not supabase.is_empty():
        context = supabase
    else:
        context = _load_repo_context(repo_root, max_items=max_items)
    context = _with_live_system_status(context, repo_root=repo_root, max_items=max_items)
    return await _with_recent_corrections(
        context,
        conversation_id=conversation_id,
    )


def render_build_context(context: BuildContext, *, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    lines = [
        "--- CURRENT BUILD CONTEXT (advisory, bounded) ---",
        f"Source: {context.source}",
        "Use this only to avoid live amnesia about what James is building. Do not treat it as approval to write, spend, deploy, send outreach, or change doctrine.",
    ]
    if context.corrections:
        lines.append("Corrections:")
        lines.extend(context.corrections)
    if context.system_status:
        lines.append("Live system status:")
        lines.extend(f"- {item}" for item in context.system_status)
    if context.focus:
        lines.append("Focus:")
        lines.extend(f"- {item}" for item in context.focus)
    if context.active_loops:
        lines.append("Active loops:")
        lines.extend(f"- {item}" for item in context.active_loops)
    if context.open_intents:
        lines.append("Open decisions/intents:")
        lines.extend(f"- {item}" for item in context.open_intents)
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


async def _render_becoming_context(
    *,
    conversation_id: str | None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    if not conversation_id or os.environ.get("SH_BECOMING_CONTEXT_DISABLE", "").strip() == "1":
        return ""
    try:
        try:
            from .becoming import render_becoming_context
        except ImportError:
            from becoming import render_becoming_context
        return await render_becoming_context(str(conversation_id), max_chars=min(900, max_chars))
    except Exception:
        return ""


async def _with_recent_corrections(
    context: BuildContext,
    *,
    conversation_id: str | None,
) -> BuildContext:
    try:
        from .corrections import recent_corrections, render_corrections_block
    except ImportError:
        try:
            from corrections import recent_corrections, render_corrections_block
        except ImportError:
            return context

    pairs = await recent_corrections(conversation_id=conversation_id, limit=10)
    block = render_corrections_block(pairs)
    if not block:
        return context
    return replace(context, corrections=block.splitlines())


def _with_live_system_status(
    context: BuildContext,
    *,
    repo_root: Path,
    max_items: int,
) -> BuildContext:
    if os.environ.get("SH_LIVE_SYSTEM_STATUS_DISABLE", "").strip() == "1":
        return context
    try:
        try:
            from .live_system_status import collect_status, render_status_lines
        except ImportError:
            try:
                from live_system_status import collect_status, render_status_lines
            except ImportError:
                module_path = Path(__file__).with_name("live_system_status.py")
                spec = importlib.util.spec_from_file_location("live_system_status", module_path)
                if not spec or not spec.loader:
                    return context
                module = importlib.util.module_from_spec(spec)
                sys.modules["live_system_status"] = module
                spec.loader.exec_module(module)
                collect_status = module.collect_status
                render_status_lines = module.render_status_lines

        snapshot = collect_status(repo_root, max_items=max_items)
        lines = render_status_lines(snapshot, max_items=max_items)
    except Exception:
        return context
    if not lines:
        return context
    return replace(context, system_status=lines)


async def _load_supabase_context(*, max_items: int) -> BuildContext | None:
    url = os.environ.get("FPAI_SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("FPAI_SUPABASE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return None
    table = os.environ.get("FPAI_BUILD_CONTEXT_TABLE", "build_context")
    select = os.environ.get(
        "FPAI_BUILD_CONTEXT_SELECT",
        "id,title,status,route,weight,next,focus,active_loop,updated_at",
    )
    endpoint = f"{url}/rest/v1/{table}"
    params = {
        "select": select,
        "order": "weight.desc.nullslast,updated_at.desc.nullslast",
        "limit": str(max_items),
    }
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=SUPABASE_TIMEOUT_SECONDS) as client:
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            rows = response.json()
    except Exception:
        return None
    if not isinstance(rows, list):
        return None
    return BuildContext(
        source=f"supabase:{table}",
        focus=_row_values(rows, "focus", max_items=max_items),
        active_loops=_row_values(rows, "active_loop", max_items=max_items),
        open_intents=[_format_context_row(row) for row in rows[:max_items] if isinstance(row, dict)],
    )


def _load_repo_context(repo_root: Path, *, max_items: int) -> BuildContext:
    return BuildContext(
        source="repo-mirror",
        focus=_repo_focus(repo_root, max_items=max_items),
        active_loops=_repo_active_builds(repo_root, max_items=max_items),
        open_intents=_repo_open_intents(repo_root, max_items=max_items),
    )


def _repo_focus(repo_root: Path, *, max_items: int) -> list[str]:
    now_path = repo_root / "core" / "STATE" / "NOW.md"
    if not now_path.exists():
        return []
    text = now_path.read_text(encoding="utf-8", errors="ignore")
    candidates: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(token in stripped.lower() for token in ("builder lane", "current", "next", "focus", "attention")):
            candidates.append(_clip_markdown(stripped))
        if len(candidates) >= max_items:
            break
    return candidates


def _repo_active_builds(repo_root: Path, *, max_items: int) -> list[str]:
    registry = repo_root / "core" / "BUILD" / "REGISTRY.json"
    if not registry.exists():
        return []
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rows = data.get("active_builds") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    active = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("status") in {"building", "ready", "queued"}:
            active.append(f"{row.get('slug') or row.get('id')} · {row.get('status')} · {row.get('branch')}")
        if len(active) >= max_items:
            break
    return active


def _repo_open_intents(repo_root: Path, *, max_items: int) -> list[str]:
    buildstream = repo_root / "docs" / "codex" / "INTENT_BUILDSTREAM.md"
    if not buildstream.exists():
        return []
    text = buildstream.read_text(encoding="utf-8", errors="ignore")
    intents: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or "status:" not in stripped or "route:" not in stripped:
            continue
        if "status: ready" not in stripped and "status: building" not in stripped:
            continue
        intents.append(_clip_markdown(stripped.lstrip("- ")))
        if len(intents) >= max_items:
            break
    return intents


def _row_values(rows: list[Any], key: str, *, max_items: int) -> list[str]:
    values: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get(key)
        if value:
            text = _clean(str(value))
            if text and text not in values:
                values.append(text)
        if len(values) >= max_items:
            break
    return values


def _format_context_row(row: dict[str, Any]) -> str:
    title = _clean(str(row.get("title") or row.get("id") or "intent"))
    status = _clean(str(row.get("status") or "open"))
    route = _clean(str(row.get("route") or "unset"))
    weight = row.get("weight")
    next_step = _clean(str(row.get("next") or ""))
    bits = [title, f"status={status}", f"route={route}"]
    if weight not in (None, ""):
        bits.append(f"weight={weight}")
    if next_step:
        bits.append(f"next={next_step}")
    return " · ".join(bits)


def _clip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return _clean(text)


def _clean(text: str) -> str:
    return " ".join(text.split())[:240]
