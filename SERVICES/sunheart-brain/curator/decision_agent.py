#!/usr/bin/env python3
"""Confidence-scored Decision Agent.

This is intentionally small and fail-closed. It may ask the local Claude
subscription CLI (`claude -p`) for James's likely answer, but it never uses a
metered API and it never auto-proceeds unless the returned score clears the
threshold and the decision is reversible outside reserved risk classes.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Callable

THRESHOLD = 0.85
REVERSIBLE_RISK_CLASSES = {"low", "build", "docs"}
NEVER_AUTO_RISK_CLASSES = {"money", "identity", "prod-irreversible", "canary"}

JAMES_PROFILE_STUB = {
    "style": "Prefer the reversible default that keeps the system moving.",
    "reserved_class": "Stop for money, identity, canary, public voice, legal, people, production-irreversible, or unclear irreversible choices.",
    "attention": "Reduce James's load; notify clearly and make rollback/override easy.",
}

Runner = Callable[[str], str]


def score_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Return {answer, confidence, why, reversible, auto_proceed}.

    If disabled, malformed, or Claude is unavailable, the score is valid but
    non-auto-proceeding.
    """
    reversible = is_reversible(decision)
    risk_class = normalize_risk(decision.get("risk_class") or decision.get("risk") or "")
    if os.environ.get("DECISION_AGENT_DISABLE") == "1":
        return _result("", 0.0, "Decision Agent disabled by DECISION_AGENT_DISABLE=1.", reversible, risk_class)

    runner = _run_claude_prompt
    try:
        context = load_context()
        raw = runner(build_prompt(decision, context))
        parsed = _parse_json_object(raw)
    except Exception as exc:
        return _result("", 0.0, f"Decision Agent failed closed: {exc}", reversible, risk_class)

    answer = str(parsed.get("answer") or "").strip()
    confidence = _clamp_float(parsed.get("confidence"))
    why = str(parsed.get("why") or "No rationale returned.").strip()
    if not answer:
        confidence = 0.0
        why = "Claude returned no answer; failing closed."
    return _result(answer, confidence, why, reversible, risk_class)


def build_prompt(decision: dict[str, Any], context: dict[str, Any]) -> str:
    safe_decision = _jsonable(decision)
    return (
        "You are the FPAI Decision Agent. Estimate James Sunheart's likely answer.\n"
        "Use only the supplied context. Return strict JSON only, no markdown.\n\n"
        "Rules:\n"
        "- Prefer reversible defaults that keep the loop moving.\n"
        "- Never recommend autonomous action for money, identity, canary, public voice, legal, people, secrets, or production-irreversible choices.\n"
        "- Be honest about uncertainty. Confidence must be 0.0-1.0.\n\n"
        f"James profile stub:\n{json.dumps(JAMES_PROFILE_STUB, indent=2, sort_keys=True)}\n\n"
        f"Recent corrections (last 10):\n{json.dumps(context.get('corrections', []), indent=2, sort_keys=True)}\n\n"
        f"Recent approved/reversed decisions (last 10):\n{json.dumps(context.get('decisions', []), indent=2, sort_keys=True)}\n\n"
        f"Decision:\n{json.dumps(safe_decision, indent=2, sort_keys=True)}\n\n"
        'Return exactly: {"answer":"...", "confidence":0.0, "why":"..."}'
    )


def load_context() -> dict[str, Any]:
    return {
        "corrections": _load_recent_corrections(),
        "decisions": _load_recent_decisions(),
    }


def is_reversible(decision: dict[str, Any]) -> bool:
    rollback = str(decision.get("rollback") or decision.get("rollback_plan") or "").strip()
    risk_class = normalize_risk(decision.get("risk_class") or decision.get("risk") or "")
    return bool(rollback) or risk_class in REVERSIBLE_RISK_CLASSES


def normalize_risk(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _result(answer: str, confidence: float, why: str, reversible: bool, risk_class: str) -> dict[str, Any]:
    blocked = risk_class in NEVER_AUTO_RISK_CLASSES
    auto_proceed = bool(answer) and confidence >= _threshold() and reversible and not blocked
    return {
        "answer": answer,
        "confidence": confidence,
        "why": why,
        "reversible": bool(reversible),
        "auto_proceed": bool(auto_proceed),
    }


def _run_claude_prompt(prompt: str) -> str:
    completed = subprocess.run(
        ["claude", "-p", prompt],
        check=True,
        capture_output=True,
        text=True,
        timeout=float(os.environ.get("DECISION_AGENT_TIMEOUT_SECONDS", "45")),
    )
    return completed.stdout


def _threshold() -> float:
    try:
        return float(os.environ.get("DECISION_AGENT_THRESHOLD", str(THRESHOLD)))
    except ValueError:
        return THRESHOLD


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty claude output")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("claude output was not a JSON object")
    return value


def _clamp_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _load_recent_corrections(limit: int = 10) -> list[dict[str, str]]:
    rows = _query_db(
        """
        SELECT original_response, james_correction, captured_at::text
          FROM brain_index.corrections
         ORDER BY captured_at DESC
         LIMIT %s
        """,
        (limit,),
    )
    return [
        {"bot": str(row[0] or "")[:500], "james": str(row[1] or "")[:500], "at": str(row[2] or "")}
        for row in rows
    ]


def _load_recent_decisions(limit: int = 10) -> list[dict[str, str]]:
    rows = _query_recent_decisions(limit)
    return [
        {
            "id": str(row[0] or ""),
            "question": str(row[1] or "")[:500],
            "answer": str(row[2] or "")[:500],
            "status": str(row[3] or ""),
            "at": str(row[4] or ""),
        }
        for row in rows
    ]


def _query_recent_decisions(limit: int) -> list[tuple[Any, ...]]:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
    except ImportError:
        return []
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            columns = _table_columns(conn, "decisions")
            if "id" not in columns:
                return []
            question_expr = _coalesce_expr(columns, ("question", "title", "topic", "summary"), "''")
            answer_expr = _column_expr(columns, "answer", "''")
            status_expr = _coalesce_expr(columns, ("status", "state"), "''")
            order_expr = _coalesce_raw_expr(columns, ("updated_at", "answered_at", "created_at"), "NOW()")
            sql = f"""
                SELECT id::text,
                       {question_expr} AS question,
                       {answer_expr} AS answer,
                       {status_expr} AS status,
                       {order_expr}::text AS at
                  FROM brain_index.decisions
                 WHERE lower({status_expr}) IN ('answered', 'approved', 'reversed', 'overridden')
                 ORDER BY {order_expr} DESC
                 LIMIT %s
            """
            with conn.cursor() as cur:
                cur.execute(sql, (limit,))
                return list(cur.fetchall())
    except Exception:
        return []


def _query_db(sql: str, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
    except ImportError:
        return []
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())
    except Exception:
        return []


def _table_columns(conn: Any, table: str) -> set[str]:
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


def _column_expr(columns: set[str], column: str, fallback: str) -> str:
    return f"{column}::text" if column in columns else fallback


def _coalesce_expr(columns: set[str], candidates: tuple[str, ...], fallback: str) -> str:
    present = [f"{column}::text" for column in candidates if column in columns]
    if not present:
        return fallback
    return f"COALESCE({', '.join(present)}, {fallback})"


def _coalesce_raw_expr(columns: set[str], candidates: tuple[str, ...], fallback: str) -> str:
    present = [column for column in candidates if column in columns]
    if not present:
        return fallback
    return f"COALESCE({', '.join(present)}, {fallback})"


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return json.loads(json.dumps(value, default=str))


if __name__ == "__main__":
    import sys

    payload = json.loads(sys.stdin.read() or "{}") if len(sys.argv) == 1 else json.loads(sys.argv[1])
    print(json.dumps(score_decision(payload), indent=2, sort_keys=True))
