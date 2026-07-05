#!/usr/bin/env python3
"""Verify that recent session insights affect the live bot answer path."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

DEFAULT_DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    os.environ.get("DATABASE_URL", "postgres://brain_index:changeme@127.0.0.1:25432/appflowy"),
)
REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
# Probe the LIVE bot's code path, not the repo copy — the metric must measure
# what actually runs. Falls back to the repo copy on machines without the live dir.
_LIVE_BUILD_CONTEXT = Path("/opt/sh-brain-src/curator/build_context.py")
_REPO_BUILD_CONTEXT = REPO_ROOT / "SERVICES" / "sunheart-brain" / "curator" / "build_context.py"
BUILD_CONTEXT_PATH = _LIVE_BUILD_CONTEXT if _LIVE_BUILD_CONTEXT.exists() else _REPO_BUILD_CONTEXT
_LIVE_TGBOT = Path("/opt/sh-brain-src/curator/tgbot.py")
_REPO_TGBOT = REPO_ROOT / "SERVICES" / "sunheart-brain" / "curator" / "tgbot.py"
TGBOT_PATH = _LIVE_TGBOT if _LIVE_TGBOT.exists() else _REPO_TGBOT
DEFAULT_PROBE_TIMEOUT_SECONDS = 10.0

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "answer",
    "because",
    "before",
    "being",
    "build",
    "codex",
    "context",
    "current",
    "from",
    "have",
    "into",
    "insight",
    "james",
    "latest",
    "must",
    "session",
    "should",
    "that",
    "their",
    "there",
    "this",
    "through",
    "with",
}


@dataclass(frozen=True)
class AwarenessProbe:
    ok: bool
    latest_title: str = ""
    rendered: str = ""
    reason: str = ""
    question: str = ""
    answer: str = ""
    expected_keywords: tuple[str, ...] = ()
    matched_keywords: tuple[str, ...] = ()
    behavioral_pass: bool | None = None
    context_render_continuity: bool | None = None


def latest_session_insight(db_url: str = DEFAULT_DB_URL) -> dict[str, Any] | None:
    import psycopg

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, surface, insight_type, title, body,
                       specs_affected, weight, ts::text
                  FROM brain_index.session_insights
                 WHERE (expires_at IS NULL OR expires_at > NOW())
                   AND ts > NOW() - INTERVAL '7 days'
                   AND insight_type != 'housekeeping'
                   AND title NOT LIKE 'Auto-snapshot%'
                 ORDER BY ts DESC
                 LIMIT 1
                """
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "session_id": row[1],
        "surface": row[2],
        "insight_type": row[3],
        "title": row[4],
        "body": row[5],
        "specs_affected": row[6] or [],
        "weight": row[7],
        "ts": row[8],
    }


async def verify_latest(*, db_url: str = DEFAULT_DB_URL, max_chars: int = 1800) -> AwarenessProbe:
    return await verify_context_render_continuity(db_url=db_url, max_chars=max_chars)


async def verify_context_render_continuity(
    *,
    db_url: str = DEFAULT_DB_URL,
    max_chars: int = 1800,
) -> AwarenessProbe:
    try:
        latest = latest_session_insight(db_url)
    except Exception as exc:
        return AwarenessProbe(False, reason=f"latest lookup failed: {exc}")
    if not latest:
        return AwarenessProbe(False, reason="no active session_insights rows found")

    try:
        build_context = _load_build_context_module()
        context = build_context.BuildContext(
            source="verify_awareness",
            focus=[],
            active_loops=[],
            open_intents=[],
        )
        context = await build_context._with_recent_session_insights(context, max_items=8)
        rendered = build_context.render_build_context(context, max_chars=max_chars)
    except Exception as exc:
        return AwarenessProbe(False, latest_title=str(latest.get("title") or ""), reason=f"context render failed: {exc}")

    title = str(latest.get("title") or "")
    if title and title in rendered:
        return AwarenessProbe(True, latest_title=title, rendered=rendered, context_render_continuity=True)
    return AwarenessProbe(
        False,
        latest_title=title,
        rendered=rendered,
        reason="latest title missing from bot context",
        context_render_continuity=False,
    )


async def verify_bot_response(
    *,
    db_url: str = DEFAULT_DB_URL,
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS,
    bot_answerer: Callable[[str], Awaitable[str]] | None = None,
    context_probe: Callable[[], Awaitable[AwarenessProbe]] | None = None,
) -> AwarenessProbe:
    try:
        latest = latest_session_insight(db_url)
    except Exception as exc:
        return AwarenessProbe(False, reason=f"latest lookup failed: {exc}", behavioral_pass=False)
    if not latest:
        return AwarenessProbe(False, reason="no active session_insights rows found", behavioral_pass=False)

    question = behavioral_question(latest)
    expected = expected_keywords(latest)
    continuity = await _context_probe_value(context_probe)
    try:
        if bot_answerer is None:
            answer = await ask_bot_answer_path(question, timeout_seconds=timeout_seconds)
        else:
            answer = await asyncio.wait_for(bot_answerer(question), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return AwarenessProbe(
            False,
            latest_title=str(latest.get("title") or ""),
            question=question,
            expected_keywords=tuple(expected),
            reason=f"bot answer timed out after {timeout_seconds:.1f}s",
            behavioral_pass=False,
            context_render_continuity=continuity,
        )
    except Exception as exc:
        return AwarenessProbe(
            False,
            latest_title=str(latest.get("title") or ""),
            question=question,
            expected_keywords=tuple(expected),
            reason=f"bot answer failed: {exc}",
            behavioral_pass=False,
            context_render_continuity=continuity,
        )

    passed, matched = grade_answer(answer, expected)
    return AwarenessProbe(
        passed,
        latest_title=str(latest.get("title") or ""),
        reason="ok" if passed else "behavioral bot answer missed expected latest-insight keywords",
        question=question,
        answer=answer,
        expected_keywords=tuple(expected),
        matched_keywords=tuple(matched),
        behavioral_pass=passed,
        context_render_continuity=continuity,
    )


def _load_build_context_module() -> Any:
    spec = importlib.util.spec_from_file_location("verify_awareness_build_context", BUILD_CONTEXT_PATH)
    module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
    if module is None or spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {BUILD_CONTEXT_PATH}")
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def _context_probe_value(context_probe: Callable[[], Awaitable[AwarenessProbe]] | None) -> bool | None:
    if context_probe is None:
        return None
    try:
        return (await context_probe()).ok
    except Exception:
        return None


async def ask_bot_answer_path(question: str, *, timeout_seconds: float = DEFAULT_PROBE_TIMEOUT_SECONDS) -> str:
    tgbot = _load_tgbot_module()
    original_blocks = getattr(tgbot, "_context_blocks_for_route", None)
    original_history = getattr(tgbot, "_recent_chat_history_context", None)

    def probe_blocks(_route: str) -> dict[str, bool]:
        return {
            "system_state": True,
            "buildstream": True,
            "corrections": False,
            "becoming": False,
            "brain_search": False,
        }

    async def no_history(_conversation_id: str | None, *, limit: int = 0) -> str:
        return ""

    try:
        tgbot._context_blocks_for_route = probe_blocks
        tgbot._recent_chat_history_context = no_history
        return await asyncio.wait_for(
            tgbot._synthesize_answer(
                question,
                [],
                conversation_id="awareness-behavioral-probe",
                context_route="awareness-probe",
            ),
            timeout=timeout_seconds,
        )
    finally:
        if original_blocks is not None:
            tgbot._context_blocks_for_route = original_blocks
        if original_history is not None:
            tgbot._recent_chat_history_context = original_history


def _load_tgbot_module() -> Any:
    package_dir = TGBOT_PATH.parent
    package_name = "verify_awareness_curator"
    init_path = package_dir / "__init__.py"
    if not init_path.exists():
        raise RuntimeError(f"could not load curator package for {TGBOT_PATH}")
    package_spec = importlib.util.spec_from_file_location(
        package_name,
        init_path,
        submodule_search_locations=[str(package_dir)],
    )
    package = importlib.util.module_from_spec(package_spec) if package_spec and package_spec.loader else None
    if package is None or package_spec is None or package_spec.loader is None:
        raise RuntimeError(f"could not load curator package for {TGBOT_PATH}")
    sys.modules[package_name] = package
    package_spec.loader.exec_module(package)

    spec = importlib.util.spec_from_file_location(f"{package_name}.tgbot", TGBOT_PATH)
    module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
    if module is None or spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {TGBOT_PATH}")
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def behavioral_question(insight: dict[str, Any]) -> str:
    title = " ".join(str(insight.get("title") or "").split())
    ts = " ".join(str(insight.get("ts") or "").split())
    if title:
        return (
            "Behavioral awareness check: based on the latest session insight, "
            f"what concrete issue, fix, or decision is it about? Timestamp: {ts or 'unknown'}. "
            "Answer with the key fact, not a generic status."
        )
    return (
        "Behavioral awareness check: based on the latest session insight, "
        "what concrete issue, fix, or decision is it about? Answer with the key fact."
    )


def expected_keywords(insight: dict[str, Any], *, limit: int = 12) -> list[str]:
    text = " ".join(
        str(part or "")
        for part in (
            insight.get("title"),
            insight.get("body"),
            " ".join(str(item) for item in (insight.get("specs_affected") or [])),
        )
    )
    seen: set[str] = set()
    words: list[str] = []
    for raw in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()):
        token = _stem(raw.strip("_-"))
        if len(token) < 4 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        words.append(token)
        if len(words) >= limit:
            break
    return words


def grade_answer(answer: str, expected: list[str] | tuple[str, ...]) -> tuple[bool, list[str]]:
    answer_tokens = {_stem(token) for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", answer.lower())}
    expected_tokens = [_stem(token) for token in expected if token]
    matched = [token for token in expected_tokens if token in answer_tokens]
    if not expected_tokens:
        return False, []
    required = 1 if len(expected_tokens) == 1 else 2
    if len(expected_tokens) >= 8:
        required = 3
    coverage = len(matched) / len(expected_tokens)
    return len(matched) >= required or (len(matched) >= 2 and coverage >= 0.25), matched


def _stem(token: str) -> str:
    token = token.lower().strip()
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-latest", action="store_true", help="Secondary context-render-continuity probe")
    parser.add_argument("--probe-bot-response", action="store_true", help="Primary behavioral bot-answer probe")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_PROBE_TIMEOUT_SECONDS)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.probe_latest and not args.probe_bot_response:
        print("Nothing to verify. Use --probe-bot-response or --probe-latest.", file=sys.stderr)
        return 2
    if args.probe_bot_response:
        result = asyncio.run(verify_bot_response(db_url=args.db_url, timeout_seconds=args.timeout_seconds))
    else:
        result = asyncio.run(verify_context_render_continuity(db_url=args.db_url))
    payload = {
        "ok": result.ok,
        "behavioral_pass": result.behavioral_pass,
        "context_render_continuity": result.context_render_continuity,
        "latest_title": result.latest_title,
        "question": result.question,
        "answer": result.answer,
        "expected_keywords": list(result.expected_keywords),
        "matched_keywords": list(result.matched_keywords),
        "reason": result.reason,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    elif result.ok:
        label = "bot answered latest session insight correctly" if args.probe_bot_response else "context-render-continuity"
        print(f"PASS: {label}: {result.latest_title}")
    else:
        print(f"FAIL: {result.reason}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
