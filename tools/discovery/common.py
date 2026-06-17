#!/usr/bin/env python3
"""Shared helpers for dry-run-first public contact discovery."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
MIN_DISCOVERY_SCORE = 0.4
EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.+-])", re.I)

PRIMARY_SIGNALS = (
    "fullpotential",
    "fullpotentiallife",
    "selfactualization",
    "selfrealization",
    "consciousai",
    "aiawakening",
    "consciousliving",
    "awakening",
    "personalgrowth",
)
SECONDARY_SIGNALS = (
    "growthmindset",
    "solopreneur",
    "digitalnomad",
    "costarica",
    "zenvillage",
    "humanpotential",
    "embodiedawareness",
    "spiritualai",
    "emergentai",
    "personalai",
    "aisovereignty",
    "openmodel",
    "localllm",
    "selfhostedai",
)


@dataclass(frozen=True)
class DiscoveryContact:
    handle: str
    platform: str
    source: str
    topic_signal: str
    discovery_score: float
    pool: str = "cold"
    added_by: str = "system"
    metadata: dict[str, Any] = field(default_factory=dict)

    def row(self) -> dict[str, Any]:
        data = asdict(self)
        data["discovery_score"] = round(float(self.discovery_score), 3)
        return data


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def disabled(source: str | None = None, env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    if values.get("DISCOVERY_DISABLE") == "1":
        return True
    if source and values.get(f"{source.upper()}_DISCOVER_DISABLE") == "1":
        return True
    return False


def live_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return values.get("DISCOVERY_LIVE") == "1" and values.get("DRY_RUN", "1") != "1"


def extract_email(text: str | None) -> str | None:
    match = EMAIL_RE.search(text or "")
    return match.group(1).lower() if match else None


def clean_text(text: Any, *, limit: int = 500) -> str:
    cleaned = " ".join(str(text or "").replace("\x00", " ").split())
    return cleaned[:limit]


def score_signal(text: str, *, account_age_days: int | None = None, content_length: int | None = None) -> float:
    haystack = (text or "").lower()
    compact = re.sub(r"[^a-z0-9]+", "", haystack)
    primary = sum(1 for kw in PRIMARY_SIGNALS if kw.lower() in compact)
    secondary = sum(1 for kw in SECONDARY_SIGNALS if kw.lower() in compact)
    length = content_length if content_length is not None else len(haystack)
    score = 0.25 + min(primary, 3) * 0.20 + min(secondary, 3) * 0.08
    if length >= 100:
        score += 0.10
    elif length >= 50:
        score += 0.05
    if account_age_days is not None:
        if account_age_days >= 30:
            score += 0.10
        elif account_age_days >= 7:
            score += 0.04
    return max(0.0, min(1.0, score))


def filter_for_outreach(rows: Iterable[DiscoveryContact], *, min_score: float = MIN_DISCOVERY_SCORE) -> list[DiscoveryContact]:
    return [row for row in rows if row.discovery_score >= min_score]


def connect_from_env() -> Any:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        raise RuntimeError("missing database DSN; set BRAIN_INDEX_DB_URL, DATABASE_URL, or DB_URL")
    try:
        import psycopg  # type: ignore
    except ImportError as exc:  # pragma: no cover - live-host dependency
        raise RuntimeError("psycopg is required on the live host") from exc
    return psycopg.connect(dsn, autocommit=True, connect_timeout=3)


def table_columns(conn: Any, table: str = "probe_pool") -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'brain_index'
               AND table_name = %s
            """,
            (table,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def existing_handles(conn: Any, rows: Iterable[DiscoveryContact]) -> set[tuple[str, str]]:
    wanted = {(row.handle.lower(), row.platform.lower()) for row in rows}
    if not wanted:
        return set()
    handles = [handle for handle, _platform in wanted]
    platforms = [platform for _handle, platform in wanted]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT LOWER(handle), LOWER(platform)
              FROM brain_index.probe_pool
             WHERE LOWER(handle) = ANY(%s)
               AND LOWER(platform) = ANY(%s)
            """,
            (handles, platforms),
        )
        return {(str(row[0]), str(row[1])) for row in cur.fetchall()}


def insert_contacts(conn: Any, rows: Iterable[DiscoveryContact], *, min_score: float = MIN_DISCOVERY_SCORE) -> int:
    candidates = filter_for_outreach(rows, min_score=min_score)
    seen = existing_handles(conn, candidates)
    columns = table_columns(conn, "probe_pool")
    inserted = 0
    for row in candidates:
        key = (row.handle.lower(), row.platform.lower())
        if key in seen:
            continue
        metadata = dict(row.metadata)
        metadata.setdefault("topic_signal", row.topic_signal)
        metadata.setdefault("discovery_score", round(row.discovery_score, 3))
        metadata.setdefault("source", row.source)
        fields = ["pool", "handle", "platform", "added_by"]
        values: list[Any] = [row.pool, row.handle, row.platform, row.added_by]
        if "source" in columns:
            fields.append("source")
            values.append(row.source)
        if "topic_signal" in columns:
            fields.append("topic_signal")
            values.append(row.topic_signal)
        if "discovery_score" in columns:
            fields.append("discovery_score")
            values.append(round(row.discovery_score, 3))
        if "metadata" in columns:
            fields.append("metadata")
            values.append(json.dumps(metadata, sort_keys=True))
        placeholders = ", ".join(["%s"] * len(fields))
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO brain_index.probe_pool ({', '.join(fields)}) VALUES ({placeholders})",
                tuple(values),
            )
        seen.add(key)
        inserted += 1
    return inserted


def emit(rows: Iterable[DiscoveryContact], *, inserted: int = 0, source: str = "discovery") -> dict[str, Any]:
    shaped = [row.row() for row in rows]
    return {
        "schema": "fpai.discovery.v1",
        "source": source,
        "generated_at": utc_stamp(),
        "count": len(shaped),
        "inserted": inserted,
        "dry_run": not live_enabled(),
        "rows": shaped,
    }


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="print JSON result")
    parser.add_argument("--live", action="store_true", help="write rows when DISCOVERY_LIVE=1 and DRY_RUN is not 1")


def finish_cli(rows: list[DiscoveryContact], *, source: str, args: argparse.Namespace) -> int:
    inserted = 0
    if args.live and live_enabled():
        conn = connect_from_env()
        try:
            inserted = insert_contacts(conn, rows)
        finally:
            if hasattr(conn, "close"):
                conn.close()
    payload = emit(rows, inserted=inserted, source=source)
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"{source}: found={payload['count']} inserted={inserted} dry_run={payload['dry_run']}")
    return 0


def main_disabled(source: str, *, json_mode: bool = False) -> int:
    payload = {"schema": "fpai.discovery.v1", "source": source, "disabled": True, "count": 0, "rows": []}
    print(json.dumps(payload, sort_keys=True) if json_mode else f"{source}: disabled")
    return 0


if __name__ == "__main__":  # pragma: no cover
    print("tools.discovery.common is a helper module", file=sys.stderr)
    raise SystemExit(2)
