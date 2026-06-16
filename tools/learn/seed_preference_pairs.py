#!/usr/bin/env python3
"""Export live correction rows into the preference-pair seed dataset.

This is a capture/export step only. It reads `brain_index.corrections`, appends
JSONL rows, stamps exported source rows, and logs a count to the ops ledger. It
does not train, score, deploy, route, or grant authority.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_OUTPUT = Path("/opt/fpai-build/data/preference_pairs.jsonl")
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
TABLE_SCHEMA = "brain_index"
TABLE_NAME = "corrections"


@dataclass(frozen=True)
class CorrectionColumns:
    id: str
    prompt: str
    chosen: str
    rejected: str
    exported: str
    captured_at: str | None


@dataclass(frozen=True)
class ExportResult:
    read: int
    exported: int
    output: str
    output_lines: int
    unexported_older_than_24h: int
    dry_run: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "read": self.read,
            "exported": self.exported,
            "output": self.output,
            "output_lines": self.output_lines,
            "unexported_older_than_24h": self.unexported_older_than_24h,
            "dry_run": self.dry_run,
        }


def connect(dsn: str | None = None) -> Any:
    database_url = dsn or _dsn_from_env()
    if not database_url:
        raise RuntimeError("missing database DSN; set BRAIN_INDEX_DB_URL, DATABASE_URL, or DB_URL")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required; run under the bot/build venv") from exc
    return psycopg.connect(database_url)


def export(conn: Any, *, output: Path = DEFAULT_OUTPUT, ops_ledger: Path = DEFAULT_OPS_LEDGER, dry_run: bool = False) -> ExportResult:
    columns = detect_columns(conn)
    rows = fetch_unexported(conn, columns)
    if dry_run:
        output_lines = count_lines(output)
        older = count_unexported_older_than_24h(conn, columns)
        return ExportResult(len(rows), len(rows), str(output), output_lines, older, True)

    write_pairs(rows, output)
    if rows:
        mark_exported(conn, columns, [str(row[columns.id]) for row in rows])
    commit(conn)
    output_lines = count_lines(output)
    older = count_unexported_older_than_24h(conn, columns)
    result = ExportResult(len(rows), len(rows), str(output), output_lines, older, False)
    log_ops_row(ops_ledger, result)
    return result


def detect_columns(conn: Any) -> CorrectionColumns:
    columns = set(table_columns(conn))
    required = {"id", "preference_pair_exported"}
    missing = sorted(required - columns)
    if missing:
        raise RuntimeError(
            "d021 gate not verified live: "
            f"{TABLE_SCHEMA}.{TABLE_NAME} missing required column(s): {', '.join(missing)}"
        )

    prompt = _first_existing(columns, "session_id", "conversation_id")
    chosen = _first_existing(columns, "correction_text", "james_correction")
    rejected = _first_existing(columns, "bot_response", "original_response")
    missing_aliases = []
    if not prompt:
        missing_aliases.append("session_id or conversation_id")
    if not chosen:
        missing_aliases.append("correction_text or james_correction")
    if not rejected:
        missing_aliases.append("bot_response or original_response")
    if missing_aliases:
        raise RuntimeError(f"unsupported corrections schema; missing {', '.join(missing_aliases)}")

    captured_at = "captured_at" if "captured_at" in columns else None
    return CorrectionColumns(
        id="id",
        prompt=prompt,
        chosen=chosen,
        rejected=rejected,
        exported="preference_pair_exported",
        captured_at=captured_at,
    )


def table_columns(conn: Any) -> list[str]:
    sql = """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = %s
           AND table_name = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (TABLE_SCHEMA, TABLE_NAME))
        return [str(row[0]) for row in cur.fetchall()]


def fetch_unexported(conn: Any, columns: CorrectionColumns) -> list[dict[str, Any]]:
    sql = (
        f"SELECT {q(columns.id)}, {q(columns.prompt)}, {q(columns.chosen)}, {q(columns.rejected)} "
        f"FROM {q(TABLE_SCHEMA)}.{q(TABLE_NAME)} "
        f"WHERE {q(columns.exported)} IS NULL "
        f"ORDER BY {q(columns.id)} ASC"
    )
    with conn.cursor() as cur:
        cur.execute(sql)
        return [
            {
                columns.id: row[0],
                columns.prompt: row[1],
                columns.chosen: row[2],
                columns.rejected: row[3],
            }
            for row in cur.fetchall()
        ]


def write_pairs(rows: Iterable[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(pair_from_row(row), sort_keys=True) + "\n")


def pair_from_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "prompt": str(row.get("session_id") or row.get("conversation_id") or ""),
        "chosen": str(row.get("correction_text") or row.get("james_correction") or ""),
        "rejected": str(row.get("bot_response") or row.get("original_response") or ""),
    }


def mark_exported(conn: Any, columns: CorrectionColumns, ids: list[str]) -> None:
    if not ids:
        return
    placeholders = ", ".join(["%s"] * len(ids))
    sql = (
        f"UPDATE {q(TABLE_SCHEMA)}.{q(TABLE_NAME)} "
        f"SET {q(columns.exported)} = NOW() "
        f"WHERE {q(columns.id)} IN ({placeholders})"
    )
    with conn.cursor() as cur:
        cur.execute(sql, ids)


def count_unexported_older_than_24h(conn: Any, columns: CorrectionColumns) -> int:
    if not columns.captured_at:
        return 0
    sql = (
        f"SELECT COUNT(*) FROM {q(TABLE_SCHEMA)}.{q(TABLE_NAME)} "
        f"WHERE {q(columns.exported)} IS NULL "
        f"AND {q(columns.captured_at)} < NOW() - INTERVAL '24 hours'"
    )
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return int(row[0] if row else 0)


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def proof_passes(result: ExportResult) -> bool:
    return result.output_lines > 0 and result.unexported_older_than_24h == 0


def log_ops_row(path: Path, result: ExportResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "d022.preference_seed",
        "event": "succeeded",
        "detail": f"exported {result.exported} correction preference pairs",
        "cost": "$0",
        "artifact": result.output,
        "next": "nightly 02:00 UTC preference seed cron proof",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "row_count": result.exported,
        "output_lines": result.output_lines,
        "unexported_older_than_24h": result.unexported_older_than_24h,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def commit(conn: Any) -> None:
    if hasattr(conn, "commit"):
        conn.commit()


def q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _first_existing(columns: set[str], *names: str) -> str | None:
    return next((name for name in names if name in columns), None)


def _dsn_from_env() -> str | None:
    for key in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export unexported brain_index.corrections rows to preference JSONL.")
    parser.add_argument("--dsn", default=None, help="database DSN; defaults to BRAIN_INDEX_DB_URL/DATABASE_URL/DB_URL")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--dry-run", action="store_true", help="read/count only; do not write JSONL, stamp rows, or log ops")
    parser.add_argument("--require-proof", action="store_true", help="exit nonzero unless proof condition passes")
    args = parser.parse_args(argv)

    try:
        with connect(args.dsn) as conn:
            result = export(conn, output=args.output, ops_ledger=args.ops_ledger, dry_run=args.dry_run)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2

    ok = proof_passes(result)
    print(json.dumps({"ok": ok, **result.to_json()}, sort_keys=True))
    if args.require_proof and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
