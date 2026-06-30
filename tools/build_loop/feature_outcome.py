#!/usr/bin/env python3
"""Append post-activation feature outcome rows to the ops ledger."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
VERDICTS = {"improved", "flat", "regressed", "unknown"}
REGRESSION_EVENTS = {"auto-reverted", "liveness:fail", "correction-retention:fail", "correction-loop:fail"}
UNKNOWN_EVENTS = {"liveness:planned", "liveness:skipped", "correction-retention:skipped", "correction-loop:skipped"}
PASS_EVENTS = {"liveness:pass", "correction-retention:pass", "correction-loop:pass", "activated", "auto-merged"}


def append_feature_outcome(
    path: Path | str,
    *,
    spec_id: str,
    metric_name: str,
    baseline: str,
    observed: str,
    delta: str,
    verdict: str,
    branch: str = "",
    evidence: Iterable[str] = (),
) -> dict[str, Any]:
    """Append one feature_outcome row and return it."""
    verdict = normalize_verdict(verdict)
    row = {
        "ts": utc_now(),
        "loop": "feature_outcome",
        "event": "feature_outcome",
        "detail": f"{spec_id} {metric_name}: {baseline} -> {observed} ({verdict})",
        "cost": "$0",
        "artifact": branch,
        "next": "Review regressed runtime outcome." if verdict == "regressed" else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "spec_id": spec_id,
        "metric_name": metric_name,
        "baseline": baseline,
        "observed": observed,
        "delta": delta,
        "verdict": verdict,
        "evidence": list(evidence),
    }
    ledger = Path(path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def infer_activation_outcome(
    rows: Iterable[dict[str, Any]],
    *,
    spec_id: str,
    activated: bool,
    merged: bool = True,
) -> tuple[str, str, str, list[str]]:
    """Infer observed/delta/verdict from recent ops rows for a spec."""
    evidence_rows = [row for row in rows if row_matches_spec(row, spec_id)]
    evidence = [evidence_label(row) for row in evidence_rows][-12:]
    events = {event_token(row) for row in evidence_rows}
    details = " ".join(str(row.get("detail", "")) for row in evidence_rows)
    if any(event in events or event in details for event in REGRESSION_EVENTS):
        return "post_activation_checks_failed", "runtime regression detected", "regressed", evidence
    if not merged:
        return "not_merged", "merge did not land", "unknown", evidence
    if any(event in events for event in UNKNOWN_EVENTS):
        return "post_activation_checks_incomplete", "runtime quality unknown", "unknown", evidence
    if activated or "activated" in events:
        if events & PASS_EVENTS or not evidence_rows:
            return "activated", "activation completed", "improved", evidence
    return "merged_without_activation_artifact", "no activation change detected", "flat", evidence


def append_activation_outcome(
    path: Path | str,
    *,
    spec_id: str,
    branch: str = "",
    activated: bool = False,
    merged: bool = True,
    metric_name: str = "post_merge_activation_quality",
) -> dict[str, Any]:
    rows = read_jsonl(Path(path))
    observed, delta, verdict, evidence = infer_activation_outcome(rows, spec_id=spec_id, activated=activated, merged=merged)
    return append_feature_outcome(
        path,
        spec_id=spec_id,
        metric_name=metric_name,
        baseline="merged_before_activation",
        observed=observed,
        delta=delta,
        verdict=verdict,
        branch=branch,
        evidence=evidence,
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def row_matches_spec(row: dict[str, Any], spec_id: str) -> bool:
    if row.get("event") == "feature_outcome":
        return False
    if str(row.get("spec_id") or "") == spec_id:
        return True
    return spec_id in str(row.get("detail") or "") or spec_id in str(row.get("artifact") or "")


def event_token(row: dict[str, Any]) -> str:
    event = str(row.get("event") or "")
    detail = str(row.get("detail") or "")
    if ":" in detail:
        head = detail.split(" ", 1)[0]
        if ":" in head:
            return head
    return event


def evidence_label(row: dict[str, Any]) -> str:
    event = event_token(row)
    detail = " ".join(str(row.get("detail") or "").split())
    artifact = " ".join(str(row.get("artifact") or "").split())
    if artifact:
        return f"{event} [{artifact}]: {detail}"[:260]
    return f"{event}: {detail}"[:260]


def normalize_verdict(value: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "better": "improved",
        "pass": "improved",
        "passed": "improved",
        "success": "improved",
        "same": "flat",
        "neutral": "flat",
        "failed": "regressed",
        "fail": "regressed",
        "worse": "regressed",
    }
    verdict = aliases.get(text, text)
    return verdict if verdict in VERDICTS else "unknown"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append feature_outcome rows to the ops ledger.")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--spec-id", required=True)
    parser.add_argument("--branch", default="")
    parser.add_argument("--metric-name", default="post_merge_activation_quality")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--observed", default="")
    parser.add_argument("--delta", default="")
    parser.add_argument("--verdict", default="")
    parser.add_argument("--activated", action="store_true", help="Infer from recent ledger rows as a merged+activated build.")
    args = parser.parse_args(argv)

    if args.verdict:
        row = append_feature_outcome(
            args.ops_ledger,
            spec_id=args.spec_id,
            metric_name=args.metric_name,
            baseline=args.baseline or "unknown",
            observed=args.observed or "unknown",
            delta=args.delta or "unknown",
            verdict=args.verdict,
            branch=args.branch,
        )
    else:
        row = append_activation_outcome(
            args.ops_ledger,
            spec_id=args.spec_id,
            branch=args.branch,
            activated=args.activated,
            metric_name=args.metric_name,
        )
    print(json.dumps({"ok": True, "row": row}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
