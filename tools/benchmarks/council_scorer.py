from __future__ import annotations

import datetime as dt
from typing import Any

from tools.benchmarks import rate, rows_for, score_result

AGENT = "council"


def score(data: dict[str, Any] | None = None, *, now: dt.datetime | None = None) -> dict[str, Any]:
    decisions = [row for row in rows_for(data, "decisions") if str(row.get("proposed_by") or "").lower() == "council" or bool(row.get("council_proposal"))]
    total = len(decisions)
    built = [row for row in decisions if str(row.get("build_status") or "").lower() in {"built", "done", "merged"}]
    approved = [row for row in built if str(row.get("review_status") or row.get("review") or "").upper() == "APPROVE"]
    debates = rows_for(data, "council_debates")
    converged = sum(1 for row in debates if bool(row.get("converged")) or str(row.get("convergence") or "").lower() in {"all", "3/3", "true"})
    proposal_build_rate = rate(len(built), total)
    build_approve_rate = rate(len(approved), len(built))
    build_success_rate = round(proposal_build_rate * build_approve_rate, 4)
    metrics = {
        "proposal_build_rate": proposal_build_rate,
        "build_approve_rate": build_approve_rate,
        "build_success_rate": build_success_rate,
        "convergence_rate": rate(converged, len(debates)),
    }
    return score_result(
        AGENT,
        primary_metric=build_success_rate,
        metrics=metrics,
        trigger_fired=bool(total) and build_success_rate < 0.6,
        trigger_metric="build_success_rate" if total and build_success_rate < 0.6 else None,
        trigger_reason=f"build_success_rate {build_success_rate} below 0.6" if total and build_success_rate < 0.6 else None,
    )

