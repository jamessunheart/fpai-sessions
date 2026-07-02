#!/usr/bin/env python3
"""Verify that recent session insights are visible to the bot context layer."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


@dataclass(frozen=True)
class AwarenessProbe:
    ok: bool
    latest_title: str = ""
    rendered: str = ""
    reason: str = ""


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
                 ORDER BY weight DESC, ts DESC
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
        return AwarenessProbe(True, latest_title=title, rendered=rendered)
    return AwarenessProbe(False, latest_title=title, rendered=rendered, reason="latest title missing from bot context")


def _load_build_context_module() -> Any:
    spec = importlib.util.spec_from_file_location("verify_awareness_build_context", BUILD_CONTEXT_PATH)
    module = importlib.util.module_from_spec(spec) if spec and spec.loader else None
    if module is None or spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {BUILD_CONTEXT_PATH}")
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-latest", action="store_true", help="Probe latest brain_index.session_insights row")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.probe_latest:
        print("Nothing to verify. Use --probe-latest.", file=sys.stderr)
        return 2
    result = asyncio.run(verify_latest(db_url=args.db_url))
    payload = {
        "ok": result.ok,
        "latest_title": result.latest_title,
        "reason": result.reason,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    elif result.ok:
        print(f"PASS: latest session insight is in bot context: {result.latest_title}")
    else:
        print(f"FAIL: {result.reason}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
