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
DEFAULT_HOT_STATE_MAX_CHARS = int(os.environ.get("SH_HOT_STATE_MAX_CHARS", "3500"))
DEFAULT_DIAGNOSTIC_CONTEXT_FILE = Path(
    os.environ.get("SELF_DIAGNOSTIC_CONTEXT_FILE", "/opt/fpai-build/.self_diagnostic_context.json")
)
SUPABASE_TIMEOUT_SECONDS = float(os.environ.get("SH_BUILD_CONTEXT_TIMEOUT_SECONDS", "2.0"))
DEFAULT_HOT_STATE_FILE = Path(
    os.environ.get("HOT_MEMORY_STATE_PATH", "~/.config/fpai/hot_memory/HOT_STATE.md")
).expanduser()
HOT_STATE_MAX_AGE_SECONDS = int(os.environ.get("HOT_MEMORY_MAX_AGE_SECONDS", str(30 * 60)))


@dataclass(frozen=True)
class BuildContext:
    source: str
    focus: list[str]
    active_loops: list[str]
    open_intents: list[str]
    system_status: list[str] | None = None
    corrections: list[str] | None = None
    recent_insights: list[str] | None = None
    session_progress: list[str] | None = None

    def is_empty(self) -> bool:
        return not (
            self.focus
            or self.active_loops
            or self.open_intents
            or self.system_status
            or self.corrections
            or self.recent_insights
            or self.session_progress
        )


async def build_context_system_suffix(
    *,
    repo_root: Path | str = REPO_ROOT,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_chars: int = DEFAULT_MAX_CHARS,
    conversation_id: str | None = None,
    include_system_state: bool = True,
    include_buildstream: bool = True,
    include_corrections: bool = True,
    include_becoming: bool = True,
) -> str:
    """Return a system-prompt suffix. Empty string means no injection."""
    if os.environ.get("SH_BUILD_CONTEXT_DISABLE", "").strip() == "1":
        return ""
    diagnostic = render_active_diagnostic_context(max_chars=max_chars) if include_system_state else ""
    hot_state = render_hot_state_context(max_chars=DEFAULT_HOT_STATE_MAX_CHARS)
    routed_mode = not all((include_system_state, include_buildstream, include_corrections, include_becoming))
    if hot_state and not routed_mode:
        suffix_parts = [hot_state]
        corrections = await _render_recent_corrections_context(conversation_id=conversation_id)
        if corrections:
            suffix_parts.append(corrections)
        suffix = "\n\n".join(suffix_parts)
        if diagnostic:
            suffix = diagnostic + "\n\n" + suffix
        return "\n\n" + suffix
    context = await load_build_context(
        repo_root=Path(repo_root),
        max_items=max_items,
        conversation_id=conversation_id,
        include_system_status=include_system_state,
        include_corrections=include_corrections,
        include_recent_insights=include_buildstream,
    )
    becoming = (
        await _render_becoming_context(conversation_id=conversation_id, max_chars=max_chars)
        if include_becoming
        else ""
    )
    parts: list[str] = []
    if hot_state and include_system_state:
        parts.append(hot_state)
    rendered_context = render_build_context(
        context,
        max_chars=max_chars,
        include_system_state=include_system_state,
        include_buildstream=include_buildstream,
        include_corrections=include_corrections,
        include_recent_insights=include_buildstream,
    )
    if rendered_context:
        parts.append(rendered_context)
    if becoming:
        parts.append(becoming)
    suffix = "\n\n".join(parts)
    if diagnostic:
        suffix = diagnostic + ("\n\n" + suffix if suffix else "")
    return "\n\n" + suffix if suffix else ""


def render_hot_state_context(
    *,
    path: Path | str | None = None,
    max_chars: int = DEFAULT_HOT_STATE_MAX_CHARS,
) -> str:
    """Return fresh HOT_STATE as the primary build context, or empty fallback."""
    if os.environ.get("HOT_MEMORY_DISABLE", "").strip() == "1":
        return ""
    state_path = Path(path) if path is not None else Path(os.environ.get("HOT_MEMORY_STATE_PATH", str(DEFAULT_HOT_STATE_FILE))).expanduser()
    hot_state = load_fresh_hot_state(state_path, max_age_seconds=HOT_STATE_MAX_AGE_SECONDS)
    if not hot_state:
        return ""
    lines = [
        "--- HOT STATE (primary current-memory context, bounded) ---",
        "Source: HOT_STATE.md",
        "Use this as the current cited state. If a fact is not here, say it is not in hot state instead of guessing.",
        hot_state.strip(),
    ]
    rendered = "\n".join(lines)
    if max_chars <= 0 or len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


def load_fresh_hot_state(path: Path, *, max_age_seconds: int = HOT_STATE_MAX_AGE_SECONDS) -> str:
    try:
        stat = path.stat()
    except OSError:
        return ""
    age = datetime.now(timezone.utc).timestamp() - stat.st_mtime
    if age < 0 or age > max_age_seconds:
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return ""
    return text if text else ""


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
    include_system_status: bool = True,
    include_corrections: bool = True,
    include_recent_insights: bool = True,
) -> BuildContext:
    """Prefer Supabase when configured; otherwise use repo-local mirrors."""
    supabase = await _load_supabase_context(max_items=max_items)
    context: BuildContext
    if supabase and not supabase.is_empty():
        context = supabase
    else:
        context = _load_repo_context(repo_root, max_items=max_items)
    if include_system_status:
        context = _with_live_system_status(context, repo_root=repo_root, max_items=max_items)
    if include_recent_insights:
        context = await _with_recent_session_insights(context, max_items=max_items)
        context = _with_persisted_session_progress(context, repo_root=repo_root, max_items=max_items)
    if include_corrections:
        context = await _with_recent_corrections(
            context,
            conversation_id=conversation_id,
        )
    return context


def render_build_context(
    context: BuildContext,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    include_system_state: bool = True,
    include_buildstream: bool = True,
    include_corrections: bool = True,
    include_recent_insights: bool = True,
) -> str:
    lines = [
        "--- CURRENT BUILD CONTEXT (advisory, bounded) ---",
        f"Source: {context.source}",
        "Use this only to avoid live amnesia about what James is building. Do not treat it as approval to write, spend, deploy, send outreach, or change doctrine.",
    ]
    if include_corrections and context.corrections:
        lines.append("Corrections:")
        lines.extend(context.corrections)
    if include_recent_insights and context.recent_insights:
        lines.append("Recent decisions (all surfaces):")
        lines.extend(f"- {item}" for item in context.recent_insights)
    if include_recent_insights and context.session_progress:
        lines.append("Persisted session progress:")
        lines.extend(f"- {item}" for item in context.session_progress)
    if include_system_state and context.system_status:
        status_lines = list(context.system_status)
        if not include_buildstream:
            status_lines = [
                item
                for item in status_lines
                if not item.startswith(("Build queue:", "Active build requests:"))
            ]
        lines.append("Live system status:")
        lines.extend(f"- {item}" for item in status_lines)
    if include_buildstream and context.focus:
        lines.append("Focus:")
        lines.extend(f"- {item}" for item in context.focus)
    if include_buildstream and context.active_loops:
        lines.append("Active loops:")
        lines.extend(f"- {item}" for item in context.active_loops)
    if include_buildstream and context.open_intents:
        lines.append("Open decisions/intents:")
        lines.extend(f"- {item}" for item in context.open_intents)
    if len(lines) == 3:
        return ""
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    pinned_recent_insights = (
        [f"- {item}" for item in context.recent_insights[:2]]
        if include_recent_insights and context.recent_insights
        else []
    )
    if pinned_recent_insights:
        return _render_with_pinned_recent_insights(lines, pinned_recent_insights, max_chars=max_chars)
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


def _render_with_pinned_recent_insights(lines: list[str], pinned_recent_insights: list[str], *, max_chars: int) -> str:
    """Bound context while preserving the newest/probe-critical insight lines."""
    if max_chars <= 0:
        return ""
    bounded_marker = "- ... bounded"
    base = list(lines[:3])
    output = [*base, "Recent decisions (all surfaces):"]
    for pinned_line in pinned_recent_insights:
        candidate = "\n".join([*output, pinned_line, bounded_marker])
        if len(candidate) <= max_chars:
            output.append(pinned_line)
            continue
        room = max_chars - len("\n".join([*output, "", bounded_marker]))
        clipped = pinned_line[: max(0, room)].rstrip()
        if clipped:
            output.append(clipped)
        break
    skipped_pinned: set[str] = set()
    for line in lines[3:]:
        if line == "Recent decisions (all surfaces):":
            continue
        if line in pinned_recent_insights and line not in skipped_pinned:
            skipped_pinned.add(line)
            continue
        candidate = "\n".join([*output, line, bounded_marker])
        if len(candidate) > max_chars:
            break
        output.append(line)
    rendered = "\n".join([*output, bounded_marker])
    if len(rendered) <= max_chars:
        return rendered
    return rendered[:max_chars]


async def _with_recent_session_insights(context: BuildContext, *, max_items: int) -> BuildContext:
    if os.environ.get("SH_SESSION_INSIGHTS_DISABLE", "").strip() == "1":
        return context
    try:
        try:
            from .db import connect
        except ImportError:
            try:
                from db import connect
            except ImportError:
                module_path = Path(__file__).with_name("db.py")
                spec = importlib.util.spec_from_file_location("build_context_db", module_path)
                module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
                if module is None or spec is None or spec.loader is None:
                    return context
                sys.modules["build_context_db"] = module
                spec.loader.exec_module(module)
                connect = module.connect
    except ImportError:
        return context

    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                where_clause = """
                     WHERE ts > NOW() - INTERVAL '7 days'
                       AND (expires_at IS NULL OR expires_at > NOW())
                       AND insight_type != 'housekeeping'
                       AND title NOT LIKE 'Auto-snapshot%'
                """
                await cur.execute(
                    f"""
                    SELECT insight_type, title, body, specs_affected, weight, surface, ts::text
                      FROM brain_index.session_insights
                    {where_clause}
                     ORDER BY ts DESC
                     LIMIT 1
                    """
                )
                latest_rows = await cur.fetchall()
                await cur.execute(
                    f"""
                    SELECT insight_type, title, body, specs_affected, weight, surface, ts::text
                      FROM brain_index.session_insights
                    {where_clause}
                     ORDER BY ts DESC, weight DESC
                     LIMIT %s
                    """,
                    (max(1, max_items),),
                )
                ranked_rows = await cur.fetchall()
    except Exception:
        return context

    rows = _dedupe_session_insight_rows([*latest_rows, *ranked_rows])[: max(1, max_items)]
    rendered = [_format_session_insight_row(row) for row in rows]
    rendered = [item for item in rendered if item]
    if not rendered:
        return context
    source = context.source
    if "session_insights" not in source:
        source = f"{source}+session_insights"
    return replace(context, source=source, recent_insights=rendered)


def _dedupe_session_insight_rows(rows: list[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        try:
            _insight_type, title, _body, _specs, _weight, surface, ts = row
        except Exception:
            deduped.append(row)
            continue
        key = (str(surface or ""), str(title or ""), str(ts or ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _format_session_insight_row(row: Any) -> str:
    try:
        insight_type, title, body, specs, weight, surface, _ts = row
    except Exception:
        return ""
    spec_text = ""
    if specs:
        if isinstance(specs, (list, tuple)):
            spec_text = f" · specs={', '.join(str(item) for item in specs[:4])}"
        else:
            spec_text = f" · specs={_clean(str(specs))}"
    body_text = _clean(str(body or ""))
    suffix = f" — {body_text}" if body_text else ""
    return f"w{weight} {surface}/{insight_type}: {_clean(str(title or 'insight'))}{spec_text}{suffix}"


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


async def _render_recent_corrections_context(*, conversation_id: str | None) -> str:
    try:
        from .corrections import recent_corrections, render_corrections_block
    except ImportError:
        try:
            from corrections import recent_corrections, render_corrections_block
        except ImportError:
            return ""

    pairs = await recent_corrections(conversation_id=conversation_id, limit=10)
    return render_corrections_block(pairs)


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


def _with_persisted_session_progress(context: BuildContext, *, repo_root: Path, max_items: int) -> BuildContext:
    if os.environ.get("SH_SESSION_PERSISTENCE_DISABLE", "").strip() == "1":
        return context
    try:
        module_path = Path(repo_root) / "tools" / "continuity" / "session_persistence.py"
        spec = importlib.util.spec_from_file_location("fpai_session_persistence", module_path)
        module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
        if module is None or spec is None or spec.loader is None:
            return context
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        snapshot = module.load_latest()
        if snapshot is None:
            return context
        rendered = module.render_snapshot(snapshot, max_items=max_items, max_chars=900)
    except Exception:
        return context
    rows = [
        _clean(line.lstrip("- ").strip())
        for line in rendered.splitlines()
        if line.strip() and line.strip() != "Persisted session progress:"
    ]
    if not rows:
        return context
    source = context.source
    if "session_persistence" not in source:
        source = f"{source}+session_persistence"
    return replace(context, source=source, session_progress=rows[: max_items + 4])


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
