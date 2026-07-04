#!/usr/bin/env python3
"""Reset or surface build decisions orphaned before branch creation."""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
from typing import Any

DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)


@dataclasses.dataclass(frozen=True)
class ReapResult:
    reset: tuple[str, ...]
    blocked: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.reset) + len(self.blocked)

    def payload(self) -> dict[str, Any]:
        return {
            "reset": list(self.reset),
            "blocked": list(self.blocked),
            "count": self.count,
        }


def connect() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit(f"psycopg unavailable: {exc}") from exc
    return psycopg.connect(DB_URL, autocommit=False)


def ensure_build_attempts_column(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "ALTER TABLE IF EXISTS brain_index.decisions "
            "ADD COLUMN IF NOT EXISTS build_attempts INTEGER DEFAULT 0"
        )
        cur.execute(
            "UPDATE brain_index.decisions "
            "SET build_attempts = 0 "
            "WHERE build_attempts IS NULL"
        )
        cur.execute(
            "ALTER TABLE IF EXISTS brain_index.decisions "
            "ALTER COLUMN build_attempts SET DEFAULT 0"
        )


def reap_orphaned_decisions(
    conn: Any,
    *,
    older_minutes: int = 30,
    retry_limit: int = 2,
) -> ReapResult:
    if older_minutes < 1:
        raise ValueError("older_minutes must be >= 1")
    if retry_limit < 1:
        raise ValueError("retry_limit must be >= 1")

    reset: list[str] = []
    blocked: list[str] = []
    interval = f"{older_minutes} minutes"

    ensure_build_attempts_column(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text, COALESCE(build_attempts, 0) AS build_attempts
              FROM brain_index.decisions
             WHERE COALESCE(spec_written, false) = true
               AND lower(COALESCE(build_status, 'none')) = 'none'
               AND COALESCE(build_branch, '') = ''
               AND COALESCE(updated_at, created_at, NOW()) < NOW() - (%s::text)::interval
             ORDER BY COALESCE(updated_at, created_at), id::text
             FOR UPDATE
            """,
            (interval,),
        )
        rows = cur.fetchall()

        for decision_id, attempts in rows:
            attempts = int(attempts or 0)
            if attempts < retry_limit:
                cur.execute(
                    """
                    UPDATE brain_index.decisions
                       SET spec_written = false,
                           build_attempts = COALESCE(build_attempts, 0) + 1,
                           updated_at = NOW()
                     WHERE id::text = %s
                    """,
                    (str(decision_id),),
                )
                reset.append(str(decision_id))
            else:
                cur.execute(
                    """
                    UPDATE brain_index.decisions
                       SET build_status = 'blocked',
                           updated_at = NOW()
                     WHERE id::text = %s
                    """,
                    (str(decision_id),),
                )
                blocked.append(str(decision_id))

    conn.commit()
    return ReapResult(reset=tuple(reset), blocked=tuple(blocked))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--older-minutes", type=int, default=30)
    parser.add_argument("--retry-limit", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with connect() as conn:
        result = reap_orphaned_decisions(
            conn,
            older_minutes=args.older_minutes,
            retry_limit=args.retry_limit,
        )

    if args.json:
        print(json.dumps(result.payload(), sort_keys=True))
    elif result.count:
        bits = []
        if result.reset:
            bits.append(f"reset={','.join(result.reset)}")
        if result.blocked:
            bits.append(f"blocked={','.join(result.blocked)}")
        print("build-orphan-reaper: " + " ".join(bits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
