#!/usr/bin/env python3
"""Add the permanent build-loop canary to `brain_index.decisions`.

Safe on a live Postgres DB:
- additive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
- idempotent `INSERT ... ON CONFLICT (id) DO UPDATE`
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CURATOR_ROOT = REPO_ROOT / "SERVICES" / "sunheart-brain"
if str(CURATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(CURATOR_ROOT))

from curator import decisions


@dataclass(frozen=True)
class MigrationResult:
    altered: bool
    seeded: bool
    canary_id: str = decisions.CANARY_ID

    def to_json(self) -> dict[str, Any]:
        return {"altered": self.altered, "seeded": self.seeded, "canary_id": self.canary_id}


def connect(dsn: str | None = None) -> Any:
    database_url = dsn or _dsn_from_env()
    if not database_url:
        raise RuntimeError("missing database DSN; set BRAIN_INDEX_DB_URL, DATABASE_URL, or DB_URL")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required; run under the bot/build venv") from exc
    return psycopg.connect(database_url)


def migrate(conn: Any) -> MigrationResult:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE brain_index.decisions ADD COLUMN IF NOT EXISTS is_canary boolean DEFAULT false")
        cur.execute(
            """
            INSERT INTO brain_index.decisions
                (id, question, status, needs_build, spec_written, is_canary, created_at, updated_at)
            VALUES
                (%s, %s, 'answered', true, false, true, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE
               SET question = EXCLUDED.question,
                   status = EXCLUDED.status,
                   needs_build = EXCLUDED.needs_build,
                   spec_written = EXCLUDED.spec_written,
                   is_canary = EXCLUDED.is_canary,
                   updated_at = NOW()
            """,
            (decisions.CANARY_ID, decisions.CANARY_QUESTION),
        )
    if hasattr(conn, "commit"):
        conn.commit()
    return MigrationResult(altered=True, seeded=True)


def _dsn_from_env() -> str | None:
    for key in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add is_canary and seed d000 build-loop canary.")
    parser.add_argument("--dsn", default=None)
    args = parser.parse_args(argv)
    try:
        with connect(args.dsn) as conn:
            result = migrate(conn)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result.to_json()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
