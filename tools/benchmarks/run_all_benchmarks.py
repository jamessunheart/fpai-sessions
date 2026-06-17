from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from tools.benchmarks import (
    DEFAULT_OPS_LEDGER,
    DEFAULT_REGISTRY,
    DEFAULT_SCORE_LEDGER,
    append_jsonl,
    load_json,
    read_jsonl,
    run_date,
)
from tools.benchmarks import beacon_scorer, council_scorer, ember_scorer, forge_scorer, hermes_scorer, loop_scorer, spark_scorer, steward_scorer
from tools.benchmarks.improvement_proposer import DEFAULT_PROPOSAL_LOG, propose_for_score

SCORERS = (
    beacon_scorer,
    spark_scorer,
    ember_scorer,
    hermes_scorer,
    council_scorer,
    forge_scorer,
    steward_scorer,
    loop_scorer,
)

LIVE_TABLES = ("probe_pool", "probe_sessions", "corrections", "decisions", "council_debates")


def load_brain_index_snapshot() -> dict[str, list[dict[str, Any]]]:
    dsn = os.environ.get("BRAIN_INDEX_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        return {}
    try:
        import psycopg  # type: ignore
    except ImportError:
        try:
            import psycopg2 as psycopg  # type: ignore
        except ImportError:
            return {}
    snapshot: dict[str, list[dict[str, Any]]] = {}
    try:
        with psycopg.connect(dsn) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cur:
                for table in LIVE_TABLES:
                    cur.execute(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'brain_index' AND table_name = %s)",
                        (table,),
                    )
                    exists = cur.fetchone()[0]
                    if not exists:
                        continue
                    cur.execute(f'SELECT row_to_json(t) FROM brain_index."{table}" AS t LIMIT 5000')
                    snapshot[table] = [row[0] for row in cur.fetchall() if isinstance(row[0], dict)]
    except Exception:
        return snapshot
    return snapshot


def build_context(fixture: Path | None, *, score_ledger: Path, registry_path: Path, ops_ledger: Path) -> dict[str, Any]:
    data: dict[str, Any] = load_json(fixture) if fixture else {}
    if not fixture:
        data.update({key: value for key, value in load_brain_index_snapshot().items() if key not in data})
    data.setdefault("per_agent_scores", read_jsonl(score_ledger))
    data.setdefault("ops_ledger", read_jsonl(ops_ledger))
    if registry_path.exists() and "registry_builds" not in data:
        try:
            data["registry_builds"] = json.loads(registry_path.read_text(encoding="utf-8")).get("active_builds", [])
        except json.JSONDecodeError:
            data["registry_builds"] = []
    return data


def ledger_row(score: dict[str, Any], *, current: dt.datetime, spec_queued: str | None = None) -> dict[str, Any]:
    return {
        "agent": score["agent"],
        "run_date": run_date(current),
        "primary_metric": score.get("primary_metric"),
        "metrics": score.get("metrics") or {},
        "trigger_fired": bool(score.get("trigger_fired")),
        "trigger_metric": score.get("trigger_metric"),
        "trigger_reason": score.get("trigger_reason"),
        "spec_queued": spec_queued,
    }


def write_baseline_if_needed(score_ledger: Path, rows: list[dict[str, Any]], *, current: dt.datetime, was_empty: bool) -> Path | None:
    if not was_empty:
        return None
    baseline = score_ledger.parent / f"baseline_{run_date(current)}.json"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text(json.dumps({"run_date": run_date(current), "scores": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return baseline


def append_ops(ops_ledger: Path, row: dict[str, Any], *, current: dt.datetime) -> None:
    append_jsonl(
        ops_ledger,
        {
            "ts": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event": "benchmark_run",
            "agent": row.get("agent"),
            "primary_metric": row.get("primary_metric"),
            "trigger_fired": row.get("trigger_fired"),
            "spec_queued": row.get("spec_queued"),
        },
    )


def run_all(
    *,
    fixture: Path | None = None,
    score_ledger: Path = DEFAULT_SCORE_LEDGER,
    proposal_log: Path = DEFAULT_PROPOSAL_LOG,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    registry_path: Path = DEFAULT_REGISTRY,
    queue_improvements: bool = True,
    current: dt.datetime | None = None,
) -> dict[str, Any]:
    if os.environ.get("BENCHMARKS_DISABLE") == "1":
        return {"disabled": True, "scores": [], "errors": []}
    now = current or dt.datetime.now(dt.timezone.utc)
    data = build_context(fixture, score_ledger=score_ledger, registry_path=registry_path, ops_ledger=ops_ledger)
    ledger_was_empty = not (score_ledger.exists() and score_ledger.read_text(encoding="utf-8").strip())
    scores: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    rows_to_write: list[dict[str, Any]] = []
    for scorer in SCORERS:
        try:
            score = scorer.score(data, now=now)
            spec_queued = None
            if queue_improvements and score.get("trigger_fired"):
                try:
                    proposal = propose_for_score(score, proposal_log=proposal_log, now=now)
                    spec_queued = str(proposal.get("spec_queued")) if proposal else None
                except Exception as exc:
                    errors.append({"agent": score.get("agent", "unknown"), "error": f"proposal failed: {exc}"})
            row = ledger_row(score, current=now, spec_queued=spec_queued)
            append_jsonl(score_ledger, row)
            append_ops(ops_ledger, row, current=now)
            scores.append(score)
            rows_to_write.append(row)
        except Exception as exc:  # error isolation is part of the runner contract
            errors.append({"agent": getattr(scorer, "AGENT", scorer.__name__), "error": str(exc)})
    baseline = write_baseline_if_needed(score_ledger, rows_to_write, current=now, was_empty=ledger_was_empty)
    return {
        "disabled": False,
        "scores": scores,
        "errors": errors,
        "score_ledger": str(score_ledger),
        "baseline": str(baseline) if baseline else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--score-ledger", type=Path, default=DEFAULT_SCORE_LEDGER)
    parser.add_argument("--proposal-log", type=Path, default=DEFAULT_PROPOSAL_LOG)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--no-proposals", action="store_true")
    args = parser.parse_args(argv)
    result = run_all(
        fixture=args.fixture,
        score_ledger=args.score_ledger,
        proposal_log=args.proposal_log,
        ops_ledger=args.ops_ledger,
        queue_improvements=not args.no_proposals,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if not result.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
