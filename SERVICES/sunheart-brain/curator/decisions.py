"""Small brain_index decision CLI used by build/merge bridge scripts."""
from __future__ import annotations

import json
import os
import sys
import importlib.util as _ilu
from pathlib import Path
from typing import Any

DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)
CANARY_ID = "d000"
CANARY_QUESTION = "Build-loop canary: should never appear in pending builds"


def _load_build_state_module() -> Any:
    repo = Path(os.environ.get("FPAI_REPO_ROOT", ""))
    candidates = []
    if repo:
        candidates.append(repo / "tools" / "build_loop" / "build_state.py")
    candidates.extend(
        [
            Path("/opt/fpai-build/FPAI_Cockpit/tools/build_loop/build_state.py"),
            Path(__file__).resolve().parents[3] / "tools" / "build_loop" / "build_state.py",
        ]
    )
    for path in candidates:
        if not path.exists():
            continue
        spec = _ilu.spec_from_file_location("fpai_build_state", path)
        if spec is None or spec.loader is None:
            continue
        mod = _ilu.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    raise RuntimeError("tools/build_loop/build_state.py not found")


_build_state = _load_build_state_module()
PENDING_BUILDS_WHERE_SQL = _build_state.PENDING_DECISION_WHERE_SQL
PENDING_BUILDS_SQL = f"""
        SELECT id::text AS id, question, answer, build_spec, proof_expected, liveness, liveness_check
          FROM brain_index.decisions
{PENDING_BUILDS_WHERE_SQL}
         ORDER BY id
"""
pending_builds_from_rows = _build_state.pending_builds_from_rows


def connect() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit(f"psycopg unavailable: {exc}") from exc
    return psycopg.connect(DB_URL, autocommit=True)


def emit_rows(sql: str, params: tuple[Any, ...] = ()) -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for row in cur.fetchall():
                description = getattr(cur, "description", None)
                if description:
                    columns = [getattr(desc, "name", desc[0]) for desc in description]
                else:
                    fallback = [
                        "id",
                        "question",
                        "answer",
                        "build_spec",
                        "proof_expected",
                        "liveness",
                        "liveness_check",
                    ]
                    columns = fallback[: len(row)]
                print(json.dumps(dict(zip(columns, row)), default=str))
    return 0


def ensure_liveness_column() -> bool:
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS liveness_check TEXT")
                cur.execute("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS liveness TEXT")
        return True
    except Exception as exc:
        print(f"warning: liveness columns not ensured: {exc}", file=sys.stderr)
        return False


def pending_merges() -> int:
    return emit_rows(
        """
        SELECT id::text AS id, build_branch
          FROM brain_index.decisions
         WHERE COALESCE(build_branch, '') <> ''
           AND COALESCE(build_status, '') = 'merge_requested'
         ORDER BY id
        """
    )


def pending_builds() -> int:
    if ensure_liveness_column():
        liveness_expr = "liveness, liveness_check"
    else:
        liveness_expr = "NULL::text AS liveness, NULL::text AS liveness_check"
    return emit_rows(
        PENDING_BUILDS_SQL.replace("liveness, liveness_check", liveness_expr, 1)
        if liveness_expr != "liveness, liveness_check"
        else PENDING_BUILDS_SQL
    )


def _legacy_pending_builds_sql(liveness_expr: str) -> str:
    return f"""
        SELECT id::text AS id, question, answer, build_spec, proof_expected, {liveness_expr}
          FROM brain_index.decisions
{PENDING_BUILDS_WHERE_SQL}
         ORDER BY id
    """


def mark_merged(decision_id: str, outcome: str) -> int:
    status = "merged" if outcome == "ok" else "merge_failed"
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE brain_index.decisions
                   SET build_status = %s,
                       needs_build = false
                 WHERE id::text = %s
                """,
                (status, str(decision_id)),
            )
    return 0


def mark_built(decision_id: str) -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE brain_index.decisions
                   SET build_status = 'built',
                       spec_written = true
                 WHERE id::text = %s
                """,
                (str(decision_id),),
            )
    return 0


def set_build_result(decision_id: str, branch: str, status: str) -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE brain_index.decisions
                   SET build_branch = %s,
                       build_status = %s
                 WHERE id::text = %s
                """,
                (branch, status, str(decision_id)),
            )
    return 0


def seed() -> int:
    payload = sys.stdin.read().strip()
    if not payload:
        return 0
    item = json.loads(payload)
    question = str(item.get("question") or item.get("title") or "").strip()
    build_spec = str(item.get("build_spec") or item.get("spec") or "").strip()
    proof_expected = str(item.get("proof_expected") or "").strip()
    liveness = item.get("liveness")
    if isinstance(liveness, (dict, list)):
        liveness_text = json.dumps(liveness, sort_keys=True)
    else:
        liveness_text = str(liveness or "").strip()
    if not question:
        raise SystemExit("seed requires question/title")
    with connect() as conn:
        with conn.cursor() as cur:
            ensure_liveness_column()
            cur.execute(
                """
                INSERT INTO brain_index.decisions
                    (question, status, needs_build, build_spec, proof_expected, liveness)
                VALUES (%s, 'answered', true, %s, %s, %s)
                RETURNING id::text
                """,
                (question, build_spec, proof_expected, liveness_text),
            )
            row = cur.fetchone()
    print(json.dumps({"id": row[0] if row else None}))
    return 0


def recommend() -> int:
    payload = sys.stdin.read().strip()
    if not payload:
        return 0
    item = json.loads(payload)
    title = str(item.get("title") or "Council recommendation").strip()
    why = str(item.get("why") or "").strip()
    build_spec = str(item.get("build_spec") or "").strip()
    question = f"{title}\n\n{why}".strip()
    with connect() as conn:
        with conn.cursor() as cur:
            ensure_liveness_column()
            cur.execute(
                """
                INSERT INTO brain_index.decisions
                    (question, status, needs_build, build_spec, proof_expected)
                VALUES (%s, 'awaiting', true, %s, %s)
                RETURNING id::text
                """,
                (question, build_spec, build_spec),
            )
            row = cur.fetchone()
    print(json.dumps({"id": row[0] if row else None, "title": title}))
    return 0


def surface() -> int:
    return 0


def list_decisions() -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, status, left(question, 160)
                  FROM brain_index.decisions
                 ORDER BY id DESC
                 LIMIT 20
                """
            )
            for decision_id, status, question in cur.fetchall():
                print(f"{decision_id} {status}: {question}")
    return 0


def recent_chats(limit: int) -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, left(text, 500)
                  FROM brain_index.tg_messages
                 ORDER BY at DESC
                 LIMIT %s
                """,
                (max(1, min(limit, 200)),),
            )
            rows = cur.fetchall()
    for role, text in reversed(rows):
        print(f"{role}: {text}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: curator.decisions pending-merges|pending-builds|mark-merged|mark-built|set-build-result|ensure-liveness-column|seed|surface|list|recent-chats|recommend", file=sys.stderr)
        return 2
    cmd = args[0]
    if cmd == "pending-merges":
        return pending_merges()
    if cmd == "pending-builds":
        return pending_builds()
    if cmd == "ensure-liveness-column":
        return 0 if ensure_liveness_column() else 1
    if cmd == "mark-merged" and len(args) >= 3:
        return mark_merged(args[1], args[2])
    if cmd == "mark-built" and len(args) >= 2:
        return mark_built(args[1])
    if cmd == "set-build-result" and len(args) >= 4:
        return set_build_result(args[1], args[2], args[3])
    if cmd == "seed":
        return seed()
    if cmd == "surface":
        return surface()
    if cmd == "list":
        return list_decisions()
    if cmd == "recent-chats":
        limit = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 30
        return recent_chats(limit)
    if cmd == "recommend":
        return recommend()
    print(f"unknown or incomplete command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
