#!/usr/bin/env python3
"""Pull FP Game Champions into brain_index.probe_pool."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.probe import rate_governor

LEADERBOARD_URL = "https://fullpotential.com/api/champion/leaderboard"
SOURCE = "fp_game_champions"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Champion:
    name: str
    email: str
    field_score: float
    last_active: datetime
    affiliate_count: int


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(str(email or "").strip()))


def parse_time(value: Any) -> datetime:
    parsed = rate_governor.parse_time(value)
    return parsed or datetime.min.replace(tzinfo=timezone.utc)


def normalize_champion(row: dict[str, Any]) -> Champion | None:
    email = str(row.get("email") or "").strip().lower()
    if not valid_email(email):
        return None
    try:
        field_score = float(row.get("field_score") or 0)
    except (TypeError, ValueError):
        field_score = 0.0
    try:
        affiliate_count = int(row.get("affiliate_count") or 0)
    except (TypeError, ValueError):
        affiliate_count = 0
    return Champion(
        name=str(row.get("name") or "").strip(),
        email=email,
        field_score=field_score,
        last_active=parse_time(row.get("last_active")),
        affiliate_count=affiliate_count,
    )


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("champions", "leaderboard", "data", "results"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def sort_champions(champions: Iterable[Champion]) -> list[Champion]:
    return sorted(champions, key=lambda c: (c.last_active, c.field_score), reverse=True)


def fetch_champions(*, url: str = LEADERBOARD_URL, urlopen: Any = urllib.request.urlopen) -> list[Champion]:
    request = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "fpai-cockpit/1.0"})
    with urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8", errors="replace")
    payload = json.loads(body)
    return sort_champions(champ for row in extract_rows(payload) if (champ := normalize_champion(row)) is not None)


def existing_handles(conn: Any, emails: list[str]) -> set[str]:
    if not emails:
        return set()
    placeholders = ", ".join(["%s"] * len(emails))
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT lower(handle) FROM brain_index.probe_pool WHERE lower(handle) IN ({placeholders})",
            tuple(email.lower() for email in emails),
        )
        return {str(row[0]).lower() for row in cur.fetchall()}


def table_columns(conn: Any, table: str) -> set[str]:
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


def champion_metadata(champ: Champion) -> str:
    return json.dumps(
        {
            "name": champ.name,
            "field_score": champ.field_score,
            "last_active": champ.last_active.isoformat(),
            "affiliate_count": champ.affiliate_count,
        },
        sort_keys=True,
    )


def insert_champions(conn: Any, champions: list[Champion], *, limit: int | None = None) -> int:
    selected = champions[:limit] if limit is not None else champions
    duplicate_handles = existing_handles(conn, [c.email for c in selected])
    try:
        columns = table_columns(conn, "probe_pool")
    except Exception:
        columns = set()
    inserted = 0
    for champ in selected:
        if champ.email.lower() in duplicate_handles:
            continue
        insert_columns = ["pool", "handle", "platform", "added_by"]
        values: list[Any] = ["warm", champ.email, "email", "system"]
        if "source" in columns:
            insert_columns.append("source")
            values.append(SOURCE)
        if "metadata" in columns:
            insert_columns.append("metadata")
            values.append(champion_metadata(champ))
        placeholders = ", ".join(["%s"] * len(values))
        column_sql = ", ".join(insert_columns)
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO brain_index.probe_pool ({column_sql}) VALUES ({placeholders})",
                tuple(values),
            )
        duplicate_handles.add(champ.email.lower())
        inserted += 1
    return inserted


def pull_into_probe_pool(
    *,
    conn: Any | None = None,
    connector: Any = rate_governor.connect_from_env,
    urlopen: Any = urllib.request.urlopen,
    limit: int | None = None,
) -> dict[str, Any]:
    champions = fetch_champions(urlopen=urlopen)
    own_conn = conn is None
    db = conn or connector()
    try:
        inserted = insert_champions(db, champions, limit=limit)
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()
    return {"fetched": len(champions), "inserted": inserted, "source": SOURCE}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull FP Game Champions into brain_index.probe_pool.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if os.environ.get("PROBE_DISABLE") == "1":
        result = {"fetched": 0, "inserted": 0, "source": SOURCE, "disabled": True}
    else:
        result = pull_into_probe_pool(limit=args.limit)
        result["disabled"] = False
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"fp_champions: fetched={result['fetched']} inserted={result['inserted']} disabled={result['disabled']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
