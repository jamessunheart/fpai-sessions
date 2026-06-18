#!/usr/bin/env python3
"""Write significant session decisions into brain_index.session_insights.

This is meant for Claude Code settle hooks. It is intentionally bounded and
fail-soft: the hook may swallow non-zero exits, while this script records a
small ops-ledger row when a write fails.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    os.environ.get("DATABASE_URL", "postgres://brain_index:changeme@127.0.0.1:25432/appflowy"),
)
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_INVALIDATION_FILE = Path(
    os.environ.get("SH_SYSTEM_PROMPT_INVALIDATION_FILE", "/var/lib/sh-brain/system_prompt.invalidate")
)
MAX_INSIGHTS_PER_SESSION = 20
ALLOWED_SURFACES = {"claude_code", "codex", "telegram", "phone", "other"}
ALLOWED_TYPES = {"decision", "architecture", "spec_queue", "feedback", "frontier", "housekeeping"}
_SPEC_RE = re.compile(r"\bd\d{2,4}\b|\bSPEC_[A-Za-z0-9_.-]+\b")


@dataclass(frozen=True)
class SessionInsight:
    insight_type: str
    title: str
    body: str = ""
    specs_affected: list[str] = field(default_factory=list)
    weight: int = 5
    expires_at: str | None = None


def load_insights(*, insights_json: str = "", insights_file: Path | None = None) -> list[SessionInsight]:
    raw: Any
    if insights_file:
        text = insights_file.read_text(encoding="utf-8")
        raw = _parse_text_payload(text)
    elif insights_json.strip():
        raw = _parse_text_payload(insights_json)
    elif os.environ.get("SESSION_INSIGHTS", "").strip():
        raw = _parse_text_payload(os.environ["SESSION_INSIGHTS"])
    else:
        return []
    if isinstance(raw, dict):
        raw = raw.get("insights") or [raw]
    if not isinstance(raw, list):
        raise ValueError("insights payload must be a JSON object, JSON list, or JSONL rows")
    return [normalize_insight(item) for item in raw[:MAX_INSIGHTS_PER_SESSION]]


def normalize_insight(item: Any) -> SessionInsight:
    if not isinstance(item, dict):
        raise ValueError("each insight must be an object")
    insight_type = _clean(str(item.get("insight_type") or item.get("type") or "decision"), limit=40)
    if insight_type not in ALLOWED_TYPES:
        raise ValueError(f"unsupported insight_type: {insight_type}")
    title = _clean(str(item.get("title") or ""), limit=240)
    if not title:
        raise ValueError("insight title is required")
    body = _clean(str(item.get("body") or item.get("summary") or ""), limit=4000)
    specs_affected = _normalize_specs(item.get("specs_affected") or item.get("specs") or [], title=title, body=body)
    weight = _normalize_weight(item.get("weight", 5))
    expires_at = item.get("expires_at")
    return SessionInsight(
        insight_type=insight_type,
        title=title,
        body=body,
        specs_affected=specs_affected,
        weight=weight,
        expires_at=_clean(str(expires_at), limit=80) if expires_at else None,
    )


def ensure_schema(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_index.session_insights (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                session_id TEXT,
                surface TEXT NOT NULL DEFAULT 'claude_code',
                insight_type TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                specs_affected TEXT[] NOT NULL DEFAULT '{}',
                weight INTEGER NOT NULL DEFAULT 5,
                expires_at TIMESTAMPTZ,
                CHECK (weight BETWEEN 1 AND 10),
                CHECK (surface IN ('claude_code', 'codex', 'telegram', 'phone', 'other')),
                CHECK (insight_type IN ('decision', 'architecture', 'spec_queue', 'feedback', 'frontier', 'housekeeping'))
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS session_insights_ts_idx ON brain_index.session_insights (ts DESC)")
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS session_insights_type_weight_idx
                ON brain_index.session_insights (insight_type, weight DESC)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS session_insights_active_idx
                ON brain_index.session_insights (weight DESC, ts DESC)
                WHERE expires_at IS NULL
            """
        )


def write_insights(conn: Any, *, session_id: str, surface: str, insights: list[SessionInsight]) -> int:
    if surface not in ALLOWED_SURFACES:
        raise ValueError(f"unsupported surface: {surface}")
    if not insights:
        return 0
    ensure_schema(conn)
    with conn.cursor() as cur:
        for insight in insights[:MAX_INSIGHTS_PER_SESSION]:
            cur.execute(
                """
                INSERT INTO brain_index.session_insights
                    (session_id, surface, insight_type, title, body, specs_affected, weight, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::timestamptz)
                """,
                (
                    session_id,
                    surface,
                    insight.insight_type,
                    insight.title,
                    insight.body,
                    insight.specs_affected,
                    insight.weight,
                    insight.expires_at,
                ),
            )
    return min(len(insights), MAX_INSIGHTS_PER_SESSION)


def invalidate_system_prompt_cache(path: Path, *, insights: Iterable[SessionInsight]) -> bool:
    if not any(insight.weight >= 8 for insight in insights):
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8")
        return True
    except Exception as exc:
        append_ops(DEFAULT_OPS_LEDGER, {"event": "session_insights_invalidation_failed", "error": str(exc)})
        return False


def append_ops(path: Path, row: dict[str, Any]) -> None:
    payload = {"ts": datetime.now(timezone.utc).isoformat(), **row}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
    except Exception:
        pass


def _connect(db_url: str) -> Any:
    import psycopg

    return psycopg.connect(db_url, autocommit=True)


def _parse_text_payload(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in stripped.splitlines() if line.strip()]
        return rows


def _normalize_specs(value: Any, *, title: str, body: str) -> list[str]:
    values: list[str]
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [str(item) for item in value]
    else:
        values = []
    values.extend(_SPEC_RE.findall(f"{title} {body}"))
    seen: set[str] = set()
    normalized: list[str] = []
    for item in values:
        cleaned = _clean(item, limit=80)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return normalized[:12]


def _normalize_weight(value: Any) -> int:
    try:
        weight = int(value)
    except (TypeError, ValueError):
        weight = 5
    return max(1, min(10, weight))


def _clean(text: str, *, limit: int) -> str:
    return " ".join((text or "").split())[:limit]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", default=os.environ.get("CLAUDE_SESSION_ID", "unknown"))
    parser.add_argument("--source", "--surface", dest="surface", default="claude_code", choices=sorted(ALLOWED_SURFACES))
    parser.add_argument("--insights", default="", help="JSON object/list or JSONL insight rows")
    parser.add_argument("--insights-file", type=Path)
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--invalidate-file", type=Path, default=DEFAULT_INVALIDATION_FILE)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        insights = load_insights(insights_json=args.insights, insights_file=args.insights_file)
    except Exception as exc:
        append_ops(args.ops_ledger, {"event": "session_insights_payload_failed", "error": str(exc)})
        print(f"session insights payload failed: {exc}", file=sys.stderr)
        return 2
    if not insights:
        result = {"written": 0, "session_id": args.session_id, "surface": args.surface}
        print(json.dumps(result, sort_keys=True) if args.json else "session insights: none to write")
        return 0
    try:
        with _connect(args.db_url) as conn:
            written = write_insights(conn, session_id=args.session_id, surface=args.surface, insights=insights)
    except Exception as exc:
        append_ops(
            args.ops_ledger,
            {
                "event": "session_insights_write_failed",
                "session_id": args.session_id,
                "surface": args.surface,
                "count": len(insights),
                "error": str(exc),
            },
        )
        print(f"session insights write failed: {exc}", file=sys.stderr)
        return 1
    invalidated = invalidate_system_prompt_cache(args.invalidate_file, insights=insights)
    append_ops(
        args.ops_ledger,
        {
            "event": "session_insights_written",
            "session_id": args.session_id,
            "surface": args.surface,
            "count": written,
            "invalidated_system_prompt": invalidated,
        },
    )
    result = {"written": written, "session_id": args.session_id, "surface": args.surface, "invalidated": invalidated}
    print(json.dumps(result, sort_keys=True) if args.json else f"session insights written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
