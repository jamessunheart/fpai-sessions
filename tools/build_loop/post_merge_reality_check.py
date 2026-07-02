#!/usr/bin/env python3
"""Daily delayed reality check for merged build decisions.

This is intentionally evidence-led. A merged decision is considered real only
when the ops ledger contains both:

- liveness proof: a `liveness:pass` / `liveness_status=live` row for the spec
- metric proof: a `feature_outcome` row with `verdict=improved` for the spec

Rows older than the grace window without both proofs are marked `merged_dead`
and get one focused repair decision queued.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)


@dataclasses.dataclass(frozen=True)
class MergedDecision:
    decision_id: str
    question: str
    build_branch: str
    build_spec: str
    proof_expected: str
    liveness: str
    merged_at: dt.datetime

    @property
    def spec_id(self) -> str:
        found = spec_id_from_text(" ".join([self.build_branch, self.build_spec, self.question]))
        return found or f"SPEC_{self.decision_id}"


@dataclasses.dataclass(frozen=True)
class LedgerEvidence:
    live: bool
    metric_moved: bool
    liveness_event: str = ""
    metric_event: str = ""


@dataclasses.dataclass(frozen=True)
class RealityVerdict:
    decision: MergedDecision
    age_days: int
    status: str
    evidence: LedgerEvidence
    reason: str

    @property
    def dead(self) -> bool:
        return self.status == "merged_dead"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def utc_now_text() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> dt.datetime | None:
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def spec_id_from_text(text: str) -> str:
    match = re.search(r"\bSPEC_[A-Za-z0-9][A-Za-z0-9_.-]*", text or "")
    return match.group(0).rstrip(".,)") if match else ""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def row_matches(row: dict[str, Any], decision: MergedDecision) -> bool:
    spec_id = decision.spec_id
    decision_id = decision.decision_id
    if str(row.get("spec_id") or "") == spec_id:
        return True
    if str(row.get("decision_id") or row.get("did") or "") == decision_id:
        return True
    haystack = " ".join(str(row.get(key) or "") for key in ("detail", "artifact", "next"))
    return spec_id in haystack or decision_id in haystack


def summarize_row(row: dict[str, Any]) -> str:
    event = str(row.get("event") or "")
    detail = " ".join(str(row.get("detail") or "").split())
    ts = str(row.get("ts") or "")
    return f"{ts} {event}: {detail}"[:280]


def collect_evidence(rows: Iterable[dict[str, Any]], decision: MergedDecision) -> LedgerEvidence:
    liveness_event = ""
    metric_event = ""
    live = False
    metric_moved = False
    for row in rows:
        if not row_matches(row, decision):
            continue
        event = str(row.get("event") or "")
        if event.startswith("liveness:") or row.get("liveness_status"):
            liveness_event = summarize_row(row)
            if event == "liveness:pass" or str(row.get("liveness_status") or "").lower() == "live":
                live = True
        if event == "feature_outcome":
            metric_event = summarize_row(row)
            if str(row.get("verdict") or "").lower() == "improved":
                metric_moved = True
    return LedgerEvidence(live=live, metric_moved=metric_moved, liveness_event=liveness_event, metric_event=metric_event)


def evaluate_decision(
    decision: MergedDecision,
    rows: Iterable[dict[str, Any]],
    *,
    now: dt.datetime | None = None,
    grace_days: int = 3,
) -> RealityVerdict:
    current = now or utc_now()
    age_days = max(0, (current - decision.merged_at).days)
    evidence = collect_evidence(rows, decision)
    missing: list[str] = []
    if not evidence.live:
        missing.append("LIVE artifact proof")
    if not evidence.metric_moved:
        missing.append("metric movement proof")
    if age_days < grace_days:
        return RealityVerdict(decision, age_days, "pending", evidence, f"inside {grace_days}-day grace window")
    if missing:
        return RealityVerdict(decision, age_days, "merged_dead", evidence, "missing " + " and ".join(missing))
    return RealityVerdict(decision, age_days, "real", evidence, "liveness and metric proof present")


def append_ops_ledger(path: Path, verdicts: Iterable[RealityVerdict], marked: Iterable[str]) -> None:
    verdict_list = list(verdicts)
    marked_list = list(marked)
    counts: dict[str, int] = {}
    for verdict in verdict_list:
        counts[verdict.status] = counts.get(verdict.status, 0) + 1
    row = {
        "ts": utc_now_text(),
        "loop": "post_merge_reality",
        "event": "post-merge-reality",
        "detail": (
            f"checked={len(verdict_list)} real={counts.get('real', 0)} "
            f"pending={counts.get('pending', 0)} merged_dead={counts.get('merged_dead', 0)}"
        ),
        "cost": "$0",
        "artifact": ",".join(marked_list),
        "next": "Repair specs auto-queued for merged_dead rows." if marked_list else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "checked": len(verdict_list),
        "real": counts.get("real", 0),
        "pending": counts.get("pending", 0),
        "merged_dead": counts.get("merged_dead", 0),
        "marked": marked_list,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_repair_spec(verdict: RealityVerdict) -> str:
    decision = verdict.decision
    return (
        f"# Repair merged-dead build {decision.decision_id}\n\n"
        "## Problem\n"
        f"`{decision.decision_id}` was marked `merged` but failed the delayed post-merge reality check "
        f"after {verdict.age_days} days: {verdict.reason}.\n\n"
        "## Required proof\n"
        "- Artifact is LIVE, evidenced by a `liveness:pass` ledger row for the original spec.\n"
        "- The stated metric moved, evidenced by a `feature_outcome` ledger row with `verdict=improved`.\n\n"
        "## Context\n"
        f"- Original spec: `{decision.spec_id}`\n"
        f"- Original branch: `{decision.build_branch}`\n"
        f"- Liveness evidence: {verdict.evidence.liveness_event or 'missing'}\n"
        f"- Metric evidence: {verdict.evidence.metric_event or 'missing'}\n\n"
        "Keep the repair scoped, reversible, tested, and do not deploy broadly, push, merge, "
        "touch secrets, send outreach, stop/delete services, or move money."
    )


def connect() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(f"psycopg unavailable: {exc}") from exc
    return psycopg.connect(DB_URL, autocommit=True)


def table_columns(conn: Any) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'brain_index'
               AND table_name = 'decisions'
            """
        )
        return {str(row[0]) for row in cur.fetchall()}


def ensure_columns(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS liveness TEXT")
        cur.execute("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS merged_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS reality_checked_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS reality_status TEXT")
        cur.execute("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS reality_detail TEXT")


def fetch_merged_decisions(conn: Any, *, now: dt.datetime, grace_days: int) -> list[MergedDecision]:
    ensure_columns(conn)
    columns = table_columns(conn)
    time_exprs = ["merged_at"]
    for candidate in ("build_updated_at", "updated_at", "created_at"):
        if candidate in columns:
            time_exprs.append(candidate)
    time_expr = "COALESCE(" + ", ".join(time_exprs) + ")"
    cutoff = now - dt.timedelta(days=grace_days)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id::text,
                   COALESCE(question, '') AS question,
                   COALESCE(build_branch, '') AS build_branch,
                   COALESCE(build_spec, '') AS build_spec,
                   COALESCE(proof_expected, '') AS proof_expected,
                   COALESCE(liveness, '') AS liveness,
                   {time_expr} AS merged_at
              FROM brain_index.decisions
             WHERE COALESCE(build_status, '') = 'merged'
               AND {time_expr} IS NOT NULL
               AND {time_expr} <= %s
             ORDER BY {time_expr} ASC
            """,
            (cutoff,),
        )
        out: list[MergedDecision] = []
        for row in cur.fetchall():
            merged_at = parse_time(row[6])
            if merged_at is None:
                continue
            out.append(
                MergedDecision(
                    decision_id=str(row[0]),
                    question=str(row[1] or ""),
                    build_branch=str(row[2] or ""),
                    build_spec=str(row[3] or ""),
                    proof_expected=str(row[4] or ""),
                    liveness=str(row[5] or ""),
                    merged_at=merged_at,
                )
            )
    return out


def mark_merged_dead(conn: Any, verdict: RealityVerdict) -> bool:
    decision = verdict.decision
    repair_id = f"{decision.decision_id}-reality-fix"
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE brain_index.decisions
               SET build_status = 'merged_dead',
                   needs_build = false,
                   reality_checked_at = NOW(),
                   reality_status = 'merged_dead',
                   reality_detail = %s
             WHERE id::text = %s
               AND COALESCE(build_status, '') = 'merged'
            """,
            (verdict.reason, decision.decision_id),
        )
        changed = getattr(cur, "rowcount", 0) == 1
        if not changed:
            return False
        cur.execute(
            """
            INSERT INTO brain_index.decisions
                (id, question, status, answer, needs_build, build_spec, proof_expected, spec_written, build_status)
            VALUES
                (%s, %s, 'answered', %s, true, %s, %s, false, 'queued')
            ON CONFLICT (id) DO NOTHING
            """,
            (
                repair_id,
                f"Repair merged-dead build {decision.decision_id}",
                f"auto-queued by d140 post-merge reality check at {utc_now_text()}",
                build_repair_spec(verdict),
                f"{decision.spec_id} has liveness:pass and feature_outcome verdict=improved after repair.",
            ),
        )
    return True


def notify_telegram(repo_root: Path, marked: Iterable[str]) -> bool:
    marked_list = list(marked)
    if not marked_list:
        return False
    message = "post-merge reality check: marked merged_dead and queued repair for " + ", ".join(marked_list[:8])
    script = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return False
    result = subprocess.run([str(script), message], cwd=repo_root, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def run_check(
    *,
    repo_root: Path = REPO_ROOT,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    grace_days: int = 3,
    dry_run: bool = False,
    notify: bool = False,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    current = now or utc_now()
    ledger_rows = read_jsonl(ops_ledger)
    marked: list[str] = []
    verdicts: list[RealityVerdict] = []
    with connect() as conn:
        decisions = fetch_merged_decisions(conn, now=current, grace_days=grace_days)
        for decision in decisions:
            verdict = evaluate_decision(decision, ledger_rows, now=current, grace_days=grace_days)
            verdicts.append(verdict)
            if verdict.dead and not dry_run and mark_merged_dead(conn, verdict):
                marked.append(decision.decision_id)
    append_ops_ledger(ops_ledger, verdicts, marked)
    notified = notify_telegram(repo_root, marked) if notify and marked and not dry_run else False
    return {
        "checked": len(verdicts),
        "marked": marked,
        "notified": notified,
        "verdicts": [
            {
                "decision_id": verdict.decision.decision_id,
                "spec_id": verdict.decision.spec_id,
                "status": verdict.status,
                "age_days": verdict.age_days,
                "reason": verdict.reason,
                "live": verdict.evidence.live,
                "metric_moved": verdict.evidence.metric_moved,
            }
            for verdict in verdicts
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--grace-days", type=int, default=int(os.environ.get("POST_MERGE_REALITY_GRACE_DAYS", "3")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--send-alert", action="store_true")
    args = parser.parse_args(argv)
    result = run_check(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        grace_days=max(1, args.grace_days),
        dry_run=args.dry_run,
        notify=args.send_alert,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
