"""Decision queue integration for the Sunheart Brain curator.

The service stores Decision Agent scores on brain_index.decisions, auto-answers
only safe reversible high-confidence decisions, and records James overrides as
weighted correction memory.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import telegram as tg
from .decision_agent import score_decision

log = logging.getLogger("curator.decisions")

DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
OVERRIDE_RE = re.compile(r"^\s*override\s+(d\d{3,})\s*:\s*(.+?)\s*$", re.IGNORECASE | re.DOTALL)

MIGRATION_SQL = """
ALTER TABLE brain_index.decisions
    ADD COLUMN IF NOT EXISTS agent_score float,
    ADD COLUMN IF NOT EXISTS agent_answer text,
    ADD COLUMN IF NOT EXISTS agent_why text;
ALTER TABLE brain_index.corrections
    ADD COLUMN IF NOT EXISTS weight float NOT NULL DEFAULT 1.0;
"""


async def migrate_agent_columns(conn: Any) -> None:
    async with conn.cursor() as cur:
        await cur.execute(MIGRATION_SQL)


async def auto_answer_if_confident(did: str) -> dict[str, Any] | None:
    """Score a surfaced decision and auto-answer if the gate allows it."""
    if os.environ.get("DECISION_AGENT_DISABLE") == "1":
        return None
    from .db import connect

    async with connect() as conn:
        await migrate_agent_columns(conn)
        decision = await _fetch_decision(conn, did)
        if not decision:
            return None
        score = score_decision(decision)
        await _write_agent_score(conn, did, score)
        if not score["auto_proceed"]:
            return None
        await _record_answer(conn, did, score["answer"], decided_by="decision-agent")
    await _send_auto_decided(did, score)
    _append_ops_ledger(
        {
            "type": "decision_agent",
            "loop": "decision-agent",
            "event": "auto_decided",
            "decision_id": did,
            "answer": score["answer"],
            "confidence": score["confidence"],
            "detail": score["why"],
            "cost": "$0",
        }
    )
    return score


async def handle_override_command(text: str, *, conversation_id: str | None = None) -> str | None:
    match = parse_override(text)
    if not match:
        return None
    did, answer = match
    from .db import connect

    async with connect() as conn:
        await migrate_agent_columns(conn)
        await write_override_correction(conn, did, answer, conversation_id=conversation_id)
        await _record_answer(conn, did, answer, decided_by="james-override")
    _append_ops_ledger(
        {
            "type": "decision_agent",
            "loop": "decision-agent",
            "event": "override",
            "decision_id": did,
            "answer": answer,
            "detail": "James override recorded as weight=2.0 correction.",
            "cost": "$0",
        }
    )
    return f"✅ Override recorded for <code>{tg._esc(did)}</code>: {tg._esc(answer[:500])}"


def parse_override(text: str) -> tuple[str, str] | None:
    match = OVERRIDE_RE.match(text or "")
    if not match:
        return None
    did = match.group(1).lower()
    answer = " ".join(match.group(2).split())
    if not answer:
        return None
    return did, answer


async def write_override_correction(
    conn: Any,
    did: str,
    answer: str,
    *,
    conversation_id: str | None = None,
) -> None:
    decision = await _fetch_decision(conn, did) or {"id": did}
    previous = str(decision.get("agent_answer") or decision.get("answer") or "(no agent answer recorded)")
    why = str(decision.get("agent_why") or "").strip()
    original = f"Decision {did} agent answer: {previous}"
    if why:
        original += f"\nWhy: {why}"
    async with conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO brain_index.corrections
                (conversation_id, original_response, james_correction, weight)
            VALUES (%s, %s, %s, %s)
            """,
            (
                str(conversation_id or f"decision:{did}"),
                original[:8000],
                f"Override {did}: {answer}"[:8000],
                2.0,
            ),
        )


async def surface_next() -> dict[str, Any] | None:
    """Mark the next open decision awaiting, then let the agent try first."""
    from .db import connect

    async with connect() as conn:
        await migrate_agent_columns(conn)
        awaiting = await _fetch_first_by_status(conn, "awaiting")
        if awaiting:
            log.info("already awaiting %s", awaiting.get("id"))
            return None
        decision = await _fetch_first_by_status(conn, "open")
        if not decision:
            log.info("no open decisions")
            return None
        did = str(decision["id"])
        await _mark_awaiting(conn, did)

    try:
        auto = await auto_answer_if_confident(did)
    except Exception as exc:
        log.warning("decision agent failed after awaiting; surfacing normal card did=%s: %s", did, exc)
        auto = None
    if auto:
        return {"id": did, "auto_decided": True, "score": auto}

    await _send_decision_card(decision)
    return {"id": did, "auto_decided": False}


async def seed(decision: dict[str, Any]) -> str:
    from .db import connect

    did = str(decision.get("id") or "").strip()
    if not did:
        did = await _next_decision_id()
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO brain_index.decisions
                    (id, question, options, risk_class, rollback, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'open', NOW())
                ON CONFLICT (id) DO UPDATE SET
                    question = EXCLUDED.question,
                    options = EXCLUDED.options,
                    risk_class = EXCLUDED.risk_class,
                    rollback = EXCLUDED.rollback
                """,
                (
                    did,
                    decision.get("question") or decision.get("title") or decision.get("summary") or "",
                    decision.get("options") or "",
                    decision.get("risk_class") or decision.get("risk") or "",
                    decision.get("rollback") or "",
                ),
            )
    return did


async def _fetch_decision(conn: Any, did: str) -> dict[str, Any] | None:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT row_to_json(d) FROM brain_index.decisions d WHERE d.id::text = %s LIMIT 1",
            (did,),
        )
        row = await cur.fetchone()
    if not row:
        return None
    value = row[0]
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


async def _fetch_first_by_status(conn: Any, status: str) -> dict[str, Any] | None:
    columns = await _decision_columns(conn)
    status_column = _first_column(columns, ("status", "state"))
    if not status_column:
        return None
    order_expr = _coalesce_raw_expr(columns, ("updated_at", "created_at"), "NOW()")
    async with conn.cursor() as cur:
        await cur.execute(
            f"""
            SELECT row_to_json(d)
              FROM brain_index.decisions d
             WHERE lower(d.{status_column}::text) = %s
             ORDER BY {order_expr} ASC
             LIMIT 1
            """,
            (status,),
        )
        row = await cur.fetchone()
    if not row:
        return None
    return row[0] if isinstance(row[0], dict) else json.loads(row[0])


async def _mark_awaiting(conn: Any, did: str) -> None:
    columns = await _decision_columns(conn)
    status_column = _first_column(columns, ("status", "state"))
    assignments = []
    params: list[Any] = []
    if status_column:
        assignments.append(f"{status_column} = %s")
        params.append("awaiting")
    if "surfaced_at" in columns:
        assignments.append("surfaced_at = COALESCE(surfaced_at, NOW())")
    if "updated_at" in columns:
        assignments.append("updated_at = NOW()")
    if not assignments:
        return
    params.append(did)
    async with conn.cursor() as cur:
        await cur.execute(
            f"""
            UPDATE brain_index.decisions
               SET {', '.join(assignments)}
             WHERE id::text = %s
            """,
            tuple(params),
        )


async def _write_agent_score(conn: Any, did: str, score: dict[str, Any]) -> None:
    columns = await _decision_columns(conn)
    assignments = []
    params: list[Any] = []
    for column, value in (
        ("agent_score", float(score["confidence"])),
        ("agent_answer", score["answer"]),
        ("agent_why", score["why"]),
    ):
        if column in columns:
            assignments.append(f"{column} = %s")
            params.append(value)
    if "updated_at" in columns:
        assignments.append("updated_at = NOW()")
    if not assignments:
        return
    params.append(did)
    async with conn.cursor() as cur:
        await cur.execute(
            f"""
            UPDATE brain_index.decisions
               SET {', '.join(assignments)}
             WHERE id::text = %s
            """,
            tuple(params),
        )


async def _record_answer(conn: Any, did: str, answer: str, *, decided_by: str) -> None:
    columns = await _decision_columns(conn)
    status_column = _first_column(columns, ("status", "state"))
    assignments = []
    params: list[Any] = []
    if status_column:
        assignments.append(f"{status_column} = %s")
        params.append("answered")
    if "answer" in columns:
        assignments.append("answer = %s")
        params.append(answer)
    if "answered_at" in columns:
        assignments.append("answered_at = NOW()")
    if "decided_by" in columns:
        assignments.append("decided_by = %s")
        params.append(decided_by)
    if "updated_at" in columns:
        assignments.append("updated_at = NOW()")
    if not assignments:
        return
    params.append(did)
    async with conn.cursor() as cur:
        await cur.execute(
            f"""
            UPDATE brain_index.decisions
               SET {', '.join(assignments)}
             WHERE id::text = %s
            """,
            tuple(params),
        )


async def _decision_columns(conn: Any) -> set[str]:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'brain_index'
               AND table_name = 'decisions'
            """
        )
        rows = await cur.fetchall()
    return {str(row[0]) for row in rows}


def _first_column(columns: set[str], candidates: tuple[str, ...]) -> str | None:
    for column in candidates:
        if column in columns:
            return column
    return None


def _coalesce_raw_expr(columns: set[str], candidates: tuple[str, ...], fallback: str) -> str:
    present = [column for column in candidates if column in columns]
    if not present:
        return fallback
    return f"COALESCE({', '.join(present)}, {fallback})"


async def _send_auto_decided(did: str, score: dict[str, Any]) -> None:
    pct = int(round(float(score["confidence"]) * 100))
    msg = (
        f"Auto-decided [<code>{tg._esc(did)}</code>]: {tg._esc(str(score['answer'])[:500])} "
        f"(confidence: {pct}%) — {tg._esc(str(score['why'])[:900])}\n"
        f"Reply <code>override {tg._esc(did)}: your answer</code> to reverse."
    )
    await tg.send(msg)


async def _send_decision_card(decision: dict[str, Any]) -> None:
    did = str(decision.get("id") or "")
    question = str(decision.get("question") or decision.get("title") or decision.get("summary") or "(untitled decision)")
    options = str(decision.get("options") or "")
    lines = [f"🟡 <b>Decision needed</b> [<code>{tg._esc(did)}</code>]", tg._esc(question)]
    if options:
        lines.append("")
        lines.append(f"Options: {tg._esc(options.replace('|', ' / '))}")
    lines.append("")
    lines.append(f"Reply: <code>{tg._esc(did)}: your answer</code>")
    await tg.send("\n".join(lines))


async def _next_decision_id() -> str:
    from .db import connect

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*)::int FROM brain_index.decisions")
            row = await cur.fetchone()
    return f"d{int(row[0] if row else 0) + 1:03d}"


def _append_ops_ledger(row: dict[str, Any], path: Path = DEFAULT_OPS_LEDGER) -> None:
    full = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **row,
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(full, sort_keys=True) + "\n")
    except Exception as exc:
        log.warning("ops ledger write failed: %s", exc)


async def _pending_builds() -> None:
    from .db import connect

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT row_to_json(d)
                  FROM brain_index.decisions d
                 WHERE lower(COALESCE(status::text, state::text, '')) = 'answered'
                   AND COALESCE(needs_build, false) = true
                   AND COALESCE(spec_written, false) = false
                 ORDER BY COALESCE(updated_at, answered_at, created_at, NOW()) ASC
                """
            )
            rows = await cur.fetchall()
    for row in rows:
        print(json.dumps(row[0], sort_keys=True))


async def _mark_built(did: str) -> None:
    from .db import connect

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE brain_index.decisions SET spec_written=true, updated_at=NOW() WHERE id::text=%s",
                (did,),
            )


async def _set_build_result(did: str, branch: str, status: str) -> None:
    from .db import connect

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE brain_index.decisions
                   SET build_branch=%s, build_status=%s, updated_at=NOW()
                 WHERE id::text=%s
                """,
                (branch, status, did),
            )


async def amain(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("surface")
    sub.add_parser("surface-next")
    sub.add_parser("pending-builds")
    sub.add_parser("seed")
    mark = sub.add_parser("mark-built")
    mark.add_argument("did")
    rec = sub.add_parser("record")
    rec.add_argument("did")
    rec.add_argument("answer")
    set_result = sub.add_parser("set-build-result")
    set_result.add_argument("parts", nargs="+")
    args = parser.parse_args(argv)

    if args.cmd in ("surface", "surface-next"):
        await surface_next()
    elif args.cmd == "seed":
        print(await seed(json.loads(os.environ.get("DECISION_JSON") or sys.stdin.read())))
    elif args.cmd == "pending-builds":
        await _pending_builds()
    elif args.cmd == "mark-built":
        await _mark_built(args.did)
    elif args.cmd == "set-build-result":
        parts = args.parts
        if len(parts) == 1:
            parts = parts[0].split()
        if len(parts) != 3:
            raise SystemExit("set-build-result requires: <did> <branch> <status>")
        await _set_build_result(parts[0], parts[1], parts[2])
    elif args.cmd == "record":
        from .db import connect

        async with connect() as conn:
            await _record_answer(conn, args.did, args.answer, decided_by="telegram")
    else:
        parser.print_help()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
