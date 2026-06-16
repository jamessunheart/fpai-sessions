#!/usr/bin/env python3
"""Decision build bridge helpers for `brain_index.decisions`.

This module is intentionally narrow: it exposes the command surface already
used by the repo-side build loop (`pending-builds`, `mark-built`,
`set-build-result`, `pending-merges`, `mark-merged`) and keeps the permanent
canary out of buildable results.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Iterable

TABLE = "brain_index.decisions"
CANARY_ID = "d000"
CANARY_QUESTION = "canary — loop liveness probe"
PENDING_BUILDS_SQL = """
    SELECT id::text,
           question::text,
           COALESCE(answer::text, '') AS answer,
           COALESCE(build_spec::text, '') AS build_spec,
           COALESCE(proof_expected::text, '') AS proof_expected
      FROM brain_index.decisions
     WHERE status = 'answered'
       AND COALESCE(needs_build, false) = true
       AND COALESCE(spec_written, false) = false
       AND COALESCE(is_canary, false) = false
     ORDER BY COALESCE(answered_at, updated_at, created_at, NOW()) ASC
"""


def connect(dsn: str | None = None) -> Any:
    database_url = dsn or _dsn_from_env()
    if not database_url:
        raise RuntimeError("missing database DSN; set BRAIN_INDEX_DB_URL, DATABASE_URL, or DB_URL")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required; run under the curator venv") from exc
    return psycopg.connect(database_url)


def pending_builds(conn: Any, *, limit: int | None = None) -> list[dict[str, Any]]:
    sql = PENDING_BUILDS_SQL
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT %s"
        params = (limit,)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [
            {
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "build_spec": row[3],
                "proof_expected": row[4],
            }
            for row in cur.fetchall()
        ]


def pending_builds_from_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pure equivalent used by tests and canary sanity checks."""
    out = []
    for row in rows:
        if row.get("status") != "answered":
            continue
        if not row.get("needs_build"):
            continue
        if row.get("spec_written"):
            continue
        if row.get("is_canary"):
            continue
        out.append(row)
    return out


def mark_built(conn: Any, did: str) -> None:
    execute(
        conn,
        f"UPDATE {TABLE} SET spec_written = true, spec_written_at = NOW(), updated_at = NOW() WHERE id = %s",
        (did,),
    )


def set_build_result(conn: Any, did: str, branch: str, status: str) -> None:
    execute(
        conn,
        f"""
        UPDATE {TABLE}
           SET build_branch = %s,
               build_status = %s,
               build_result_at = NOW(),
               updated_at = NOW()
         WHERE id = %s
        """,
        (branch, status, did),
    )


def pending_merges(conn: Any) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id::text, COALESCE(build_branch::text, '') AS build_branch
              FROM {TABLE}
             WHERE COALESCE(merge_requested, false) = true
               AND COALESCE(merged, false) = false
             ORDER BY COALESCE(updated_at, created_at, NOW()) ASC
            """
        )
        return [{"id": row[0], "build_branch": row[1]} for row in cur.fetchall()]


def mark_merged(conn: Any, did: str, result: str) -> None:
    ok = result == "ok"
    execute(
        conn,
        f"""
        UPDATE {TABLE}
           SET merged = %s,
               merge_status = %s,
               merged_at = CASE WHEN %s THEN NOW() ELSE merged_at END,
               updated_at = NOW()
         WHERE id = %s
        """,
        (ok, "merged" if ok else "merge_failed", ok, did),
    )


def seed_canary(conn: Any) -> None:
    execute(
        conn,
        f"""
        INSERT INTO {TABLE}
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
        (CANARY_ID, CANARY_QUESTION),
    )


def execute(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
    if hasattr(conn, "commit"):
        conn.commit()


def _dsn_from_env() -> str | None:
    for key in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def _print_jsonl(rows: Iterable[dict[str, Any]]) -> None:
    for row in rows:
        print(json.dumps(row, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read/update brain_index.decisions for the build loop.")
    parser.add_argument("command", choices=[
        "pending-builds",
        "mark-built",
        "set-build-result",
        "pending-merges",
        "mark-merged",
        "seed-canary",
    ])
    parser.add_argument("args", nargs="*")
    parser.add_argument("--dsn", default=None)
    ns = parser.parse_args(argv)

    try:
        with connect(ns.dsn) as conn:
            if ns.command == "pending-builds":
                _print_jsonl(pending_builds(conn))
            elif ns.command == "mark-built":
                mark_built(conn, ns.args[0])
            elif ns.command == "set-build-result":
                set_build_result(conn, ns.args[0], ns.args[1], ns.args[2])
            elif ns.command == "pending-merges":
                _print_jsonl(pending_merges(conn))
            elif ns.command == "mark-merged":
                mark_merged(conn, ns.args[0], ns.args[1])
            elif ns.command == "seed-canary":
                seed_canary(conn)
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "error": str(exc),
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
