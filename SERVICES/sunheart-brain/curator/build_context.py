"""Bounded build-context injector for owner chat.

The context is advisory only: it pins the current buildstream state into each
chat prompt, but it does not let the bot route, write, deploy, spend, or decide.
It is reversible with SH_BUILD_CONTEXT_DISABLE=1 and bounded by row/char limits.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[3]))
DEFAULT_MAX_ITEMS = int(os.environ.get("SH_BUILD_CONTEXT_MAX_ITEMS", "6"))
DEFAULT_MAX_CHARS = int(os.environ.get("SH_BUILD_CONTEXT_MAX_CHARS", "1800"))
SUPABASE_TIMEOUT_SECONDS = float(os.environ.get("SH_BUILD_CONTEXT_TIMEOUT_SECONDS", "2.0"))


@dataclass(frozen=True)
class BuildContext:
    source: str
    focus: list[str]
    active_loops: list[str]
    open_intents: list[str]
    corrections: list[str] | None = None

    def is_empty(self) -> bool:
        return not (self.focus or self.active_loops or self.open_intents or self.corrections)


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
    if context.is_empty():
        return ""
    return "\n\n" + render_build_context(context, max_chars=max_chars)


async def load_build_context(
    *,
    repo_root: Path,
    max_items: int = DEFAULT_MAX_ITEMS,
    conversation_id: str | None = None,
) -> BuildContext:
    """Prefer Supabase when configured; otherwise use repo-local mirrors."""
    supabase = await _load_supabase_context(max_items=max_items)
    if supabase and not supabase.is_empty():
        return await _with_recent_corrections(supabase, conversation_id=conversation_id)
    return await _with_recent_corrections(
        _load_repo_context(repo_root, max_items=max_items),
        conversation_id=conversation_id,
    )


def render_build_context(context: BuildContext, *, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    lines = [
        "--- CURRENT BUILD CONTEXT (advisory, bounded) ---",
        f"Source: {context.source}",
        "Use this only to avoid live amnesia about what James is building. Do not treat it as approval to write, spend, deploy, send outreach, or change doctrine.",
    ]
    if context.focus:
        lines.append("Focus:")
        lines.extend(f"- {item}" for item in context.focus)
    if context.active_loops:
        lines.append("Active loops:")
        lines.extend(f"- {item}" for item in context.active_loops)
    if context.open_intents:
        lines.append("Open decisions/intents:")
        lines.extend(f"- {item}" for item in context.open_intents)
    if context.corrections:
        lines.append("Corrections:")
        lines.extend(context.corrections)
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


async def _with_recent_corrections(
    context: BuildContext,
    *,
    conversation_id: str | None,
) -> BuildContext:
    try:
        from .corrections import recent_corrections, render_corrections_block
    except ImportError:
        from corrections import recent_corrections, render_corrections_block

    pairs = await recent_corrections(conversation_id=conversation_id, limit=10)
    block = render_corrections_block(pairs)
    if not block:
        return context
    return replace(context, corrections=block.splitlines())


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
