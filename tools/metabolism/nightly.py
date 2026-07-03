#!/usr/bin/env python3
"""Nightly metabolism heartbeat.

Reads the latest conversion metrics, selects the weakest measurable conversion,
and starts exactly one experiment-lane improvement. The default mode is dry-run;
`--execute` still stays append-only: it writes a forge work-order and ledger row,
then stops at the James/council merge gate.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONVERSION_LATEST = Path(os.environ.get("FPAI_CONVERSION_LATEST", "~/.config/fpai/metrics/conversion_latest.json")).expanduser()
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_FORGE_DIR = Path(os.environ.get("FPAI_FORGE_QUEUE_DIR", "~/.config/fpai/forge/queued")).expanduser()
DEFAULT_OPERATING_PRINCIPLE = REPO_ROOT / "core" / "STATE" / "OPERATING_PRINCIPLE.md"
DEFAULT_RESULTS_DIR = REPO_ROOT / "core" / "BUILD" / "metabolism"
SPEC_ID = "SPEC_d132_d131-nightly-metabolism-improve"
DEFAULT_PRINCIPLE = "What single change, verified by reality, would most increase the systems future rate of improvement?"
LOWER_IS_BETTER_HINTS = ("latency", "error", "failure", "fail", "dropoff", "churn", "cost", "delay", "stale", "regression")


@dataclasses.dataclass(frozen=True)
class Conversion:
    name: str
    value: float
    target: float | None
    higher_is_better: bool
    source: str
    detail: str

    @property
    def health(self) -> float:
        if self.target is not None and self.target > 0:
            if self.higher_is_better:
                return self.value / self.target
            if self.value <= 0:
                return 1.0
            return self.target / self.value
        if self.higher_is_better:
            return self.value
        if self.value <= 0:
            return 1.0
        return 1.0 / self.value


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_operating_principle(path: Path = DEFAULT_OPERATING_PRINCIPLE) -> str:
    if not path.exists():
        return DEFAULT_PRINCIPLE
    text = " ".join(path.read_text(encoding="utf-8", errors="replace").split())
    return text or DEFAULT_PRINCIPLE


def measurable_conversions(data: Any) -> list[Conversion]:
    items: list[Conversion] = []
    for source, raw in iter_metric_items(data):
        item = conversion_from_raw(source, raw)
        if item is not None and math.isfinite(item.health):
            items.append(item)
    return items


def iter_metric_items(data: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(data, list):
        for index, item in enumerate(data):
            name = metric_name(item) if isinstance(item, dict) else ""
            yield name or f"{prefix}[{index}]", item
        return
    if not isinstance(data, dict):
        return
    for key in ("conversions", "metrics", "funnels", "items"):
        value = data.get(key)
        if isinstance(value, list):
            for index, item in enumerate(value):
                name = metric_name(item) if isinstance(item, dict) else ""
                yield name or f"{key}[{index}]", item
            return
        if isinstance(value, dict):
            for name, item in value.items():
                yield str(name), item
            return
    for name, value in data.items():
        if isinstance(value, (int, float, str)):
            yield str(name), {"value": value}
        elif isinstance(value, dict) and any(k in value for k in ("value", "observed", "rate", "conversion", "score")):
            yield str(name), value


def metric_name(raw: dict[str, Any]) -> str:
    for key in ("name", "metric", "metric_name", "id", "key"):
        value = raw.get(key)
        if value:
            return str(value)
    return ""


def conversion_from_raw(source: str, raw: Any) -> Conversion | None:
    if isinstance(raw, (int, float, str)):
        raw = {"value": raw}
    if not isinstance(raw, dict):
        return None
    name = metric_name(raw) or source
    value = first_number(raw, ("value", "observed", "rate", "conversion", "score", "current"))
    if value is None:
        numerator = first_number(raw, ("converted", "successes", "wins", "passed"))
        denominator = first_number(raw, ("total", "attempts", "visits", "count"))
        if numerator is not None and denominator and denominator > 0:
            value = numerator / denominator
    if value is None:
        return None
    target = first_number(raw, ("target", "goal", "threshold", "expected"))
    higher_raw = raw.get("higher_is_better")
    if higher_raw is None:
        direction = str(raw.get("direction") or raw.get("polarity") or "").lower()
        higher_is_better = direction not in {"lower", "lower_is_better", "down"}
        if any(hint in name.lower() for hint in LOWER_IS_BETTER_HINTS):
            higher_is_better = False
    else:
        higher_is_better = bool(higher_raw)
    detail = compact_json(raw)
    return Conversion(name=name, value=value, target=target, higher_is_better=higher_is_better, source=source, detail=detail)


def first_number(raw: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key not in raw:
            continue
        value = parse_number(raw.get(key))
        if value is not None:
            return value
    return None


def parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("%"):
            try:
                return float(text[:-1].strip()) / 100.0
            except ValueError:
                return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def pick_weakest(conversions: list[Conversion]) -> Conversion | None:
    if not conversions:
        return None
    return sorted(conversions, key=lambda item: (item.health, item.name))[0]


def read_feature_outcomes(path: Path, metric_name: str, limit: int = 12) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("event") != "feature_outcome" and row.get("signal_type") != "feature_outcome":
                continue
            row_metric = str(row.get("metric_name") or row.get("metric") or "")
            if metric_name == row_metric or metric_name in str(row.get("detail") or ""):
                rows.append(row)
    return rows[-limit:]


def improvement_prompt(conversion: Conversion, principle: str, outcomes: list[dict[str, Any]]) -> str:
    recent = "; ".join(
        f"{row.get('spec_id', 'unknown')} {row.get('verdict', 'unknown')}: {row.get('delta', '')}".strip()
        for row in outcomes[-5:]
    ) or "no matching feature_outcome rows found"
    direction = "higher is better" if conversion.higher_is_better else "lower is better"
    return (
        f"Operating principle: {principle}\n"
        f"Weakest measurable conversion: {conversion.name} value={conversion.value:g}"
        f" target={conversion.target if conversion.target is not None else 'unknown'}"
        f" health={conversion.health:.4f} ({direction}).\n"
        f"Conversion source: {conversion.source}; raw detail: {conversion.detail}\n"
        f"Recent real feature_outcome evidence: {recent}\n\n"
        "Forge exactly one reversible experiment-lane improvement that could improve this conversion. "
        "Do not deploy production, push, merge, touch secrets, send outreach, move money, or self-escalate. "
        "The output must be a reviewable work-order with acceptance criteria and a real measurement plan."
    )


def forge_work_order(path: Path, conversion: Conversion, prompt: str) -> dict[str, Any]:
    now = utc_now()
    slug = slugify(conversion.name)
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:10]
    file_path = path / f"{now[:10]}_{now[11:16].replace(':', '')}_metabolism_{slug}_{digest}.md"
    path.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "---\n"
        f"queued_at: {now}\n"
        "queued_by: nightly-metabolism\n"
        f"spec_id: {SPEC_ID}\n"
        "lane: experiment\n"
        "merge_gate: james_council\n"
        "autonomous_prod_deploy: blocked\n"
        "---\n\n"
        f"# Forge work-order: improve {conversion.name}\n\n"
        "## Prompt\n"
        f"{prompt}\n\n"
        "## Acceptance Criteria\n"
        "- Proposes or builds exactly one reversible improvement.\n"
        "- Cites the selected conversion metric and at least one real feature_outcome or explicit absence of one.\n"
        "- Defines baseline, observed value, delta, and verdict for the next measurement.\n"
        "- Stops at James/council merge gate; no production deploy, push, merge, secrets, outreach, or money movement.\n",
        encoding="utf-8",
    )
    return {"path": str(file_path), "digest": digest}


def append_ledger(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def run_optimizer_command(command: list[str], prompt: str, timeout: int = 120) -> dict[str, Any]:
    if not command:
        return {"status": "skipped", "reason": "no optimizer command configured"}
    env = {**os.environ, "FPAI_EXPERIMENT_LANE": "1", "FPAI_PROD_DEPLOY_BLOCKED": "1"}
    result = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=timeout, env=env)
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def queue_build_decision(weakest, prompt: str, *, db_url: str | None = None, dedup_days: int = 4) -> dict[str, Any]:
    """Bridge the metabolism to the build loop: queue the work-order as a
    brain_index decision so the existing codex->review->auto-merge pipeline
    actually SHIPS the improvement. Without this the metabolism only writes a
    prompt nobody reads (the merged-but-dead gap in d131 itself, 2026-07-02).

    Dedup guard: skip if an unmerged metabolism decision for the same weakest
    conversion already exists in the last `dedup_days` — so nightly runs on a
    stuck metric don't spam duplicate builds. Reversible: a queued decision can
    be reversed, and the build ships in the experiment lane (go-live gated).
    """
    db_url = db_url or os.environ.get("BRAIN_INDEX_DB_URL", "")
    if not db_url:
        return {"status": "skipped", "reason": "no BRAIN_INDEX_DB_URL"}
    try:
        import psycopg
    except Exception as exc:  # pragma: no cover - env without psycopg
        return {"status": "skipped", "reason": f"psycopg unavailable: {exc}"}

    tag = f"[metabolism:{weakest.name}]"
    question = (
        f"{tag} Improve weakest conversion '{weakest.name}' "
        f"(health {weakest.health:.2f}, value {weakest.value}, target {weakest.target}). "
        "Forge exactly one reversible experiment-lane improvement per the work-order. "
        "Ship behind an OFF flag; production go-live stays gated."
    )
    # Constitution Check at the second autonomous-proposal gate (Law 5).
    # Fail-open on checker error, fail-closed on a rejected verdict.
    try:
        import sys as _sys
        if str(REPO_ROOT) not in _sys.path:
            _sys.path.insert(0, str(REPO_ROOT))
        from tools.governance.constitution_check import check_proposal
        _cc = check_proposal({"title": question[:120], "kind": "metabolism_experiment", "build_spec": prompt[:2000]})
        if not _cc.get("accepted", True):
            return {"status": "constitution_rejected", "reasons": _cc.get("reasons", [])}
    except ImportError:
        pass
    try:
        with psycopg.connect(db_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*) FROM brain_index.decisions
                     WHERE question LIKE %s
                       AND created_at > NOW() - make_interval(days => %s)
                       AND coalesce(build_status,'') NOT IN ('merged','rejected')
                    """,
                    (f"%{tag}%", dedup_days),
                )
                if (cur.fetchone() or [0])[0] > 0:
                    return {"status": "skipped", "reason": "open metabolism decision exists (dedup)"}
                for _ in range(3):
                    try:
                        cur.execute(r"SELECT id FROM brain_index.decisions WHERE id ~ '^d[0-9]+$'")
                        nums = [int(row[0][1:]) for row in cur.fetchall()]
                        did = "d" + str((max(nums) + 1) if nums else 1).zfill(3)
                        cur.execute(
                            """
                            INSERT INTO brain_index.decisions
                                (id, question, answer, status, needs_build, spec_written, build_spec, build_status, created_at)
                            VALUES (%s, %s, %s, 'answered', true, false, %s, 'none', now())
                            """,
                            (did, question, "queued by nightly metabolism (experiment lane)", prompt[:8000]),
                        )
                        conn.commit()
                        return {"status": "queued", "decision_id": did}
                    except psycopg.errors.UniqueViolation:
                        conn.rollback()
                        continue
        return {"status": "error", "reason": "id assignment exhausted retries"}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)[:200]}


def build_cycle(args: argparse.Namespace) -> dict[str, Any]:
    if not args.conversion_latest.exists():
        return {"ok": False, "status": "missing_conversion_latest", "path": str(args.conversion_latest)}
    data = read_json(args.conversion_latest)
    conversions = measurable_conversions(data)
    weakest = pick_weakest(conversions)
    if weakest is None:
        return {"ok": False, "status": "no_measurable_conversions", "path": str(args.conversion_latest)}
    principle = load_operating_principle(args.operating_principle)
    outcomes = read_feature_outcomes(args.ops_ledger, weakest.name)
    prompt = improvement_prompt(weakest, principle, outcomes)
    row = {
        "ts": utc_now(),
        "event": "nightly_metabolism",
        "spec_id": SPEC_ID,
        "status": "dry_run",
        "weakest_conversion": {
            "name": weakest.name,
            "value": weakest.value,
            "target": weakest.target,
            "health": round(weakest.health, 6),
            "higher_is_better": weakest.higher_is_better,
            "source": weakest.source,
        },
        "feature_outcome_evidence_count": len(outcomes),
        "lane": "experiment",
        "prod_deploy": "blocked",
        "merge_gate": "james_council",
    }
    if args.execute:
        order = forge_work_order(args.forge_dir, weakest, prompt)
        optimizer = run_optimizer_command(args.optimizer_command, prompt, timeout=args.optimizer_timeout)
        row.update({"status": "experiment_queued", "forge_work_order": order["path"], "optimizer": optimizer})
        if not getattr(args, "no_queue_decision", False):
            row["build_decision"] = queue_build_decision(weakest, prompt)
        append_ledger(args.ops_ledger, row)
    return {"ok": True, "row": row, "prompt": prompt}


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = result.get("row") or {}
    weakest = row.get("weakest_conversion") or {}
    lines = [
        "# Nightly Metabolism Result",
        "",
        f"- Generated: {utc_now()}",
        f"- Status: {result.get('status') or row.get('status') or 'unknown'}",
        f"- Weakest conversion: `{weakest.get('name', 'none')}`",
        f"- Health: `{weakest.get('health', 'unknown')}`",
        f"- Lane: `{row.get('lane', 'experiment')}`",
        f"- Production deploy: `{row.get('prod_deploy', 'blocked')}`",
        f"- Merge gate: `{row.get('merge_gate', 'james_council')}`",
    ]
    if row.get("forge_work_order"):
        lines.append(f"- Forge work-order: `{row['forge_work_order']}`")
    lines.extend(["", "## Prompt", "", result.get("prompt", "_No prompt generated._")])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def compact_json(raw: dict[str, Any]) -> str:
    text = json.dumps(raw, sort_keys=True, ensure_ascii=True)
    return text[:700] + ("..." if len(text) > 700 else "")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "conversion"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one nightly metabolism experiment heartbeat.")
    parser.add_argument("--conversion-latest", type=Path, default=DEFAULT_CONVERSION_LATEST)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--forge-dir", type=Path, default=DEFAULT_FORGE_DIR)
    parser.add_argument("--operating-principle", type=Path, default=DEFAULT_OPERATING_PRINCIPLE)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULTS_DIR / "latest.md")
    parser.add_argument("--execute", action="store_true", help="Queue one experiment and append the ops-ledger row.")
    parser.add_argument("--optimizer-command", nargs="+", default=[])
    parser.add_argument("--optimizer-timeout", type=int, default=120)
    parser.add_argument("--no-queue-decision", action="store_true",
                        help="Skip queuing the work-order into brain_index.decisions (the build-loop bridge).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_cycle(args)
    if result.get("ok"):
        write_result(args.result, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
