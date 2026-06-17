from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from tools.benchmarks import REPO_ROOT, age_days, per_day, rate, rows_for, score_result

AGENT = "ember"
DEFAULT_ALIGNMENT = REPO_ROOT / "core" / "STATE" / "identity" / "ALIGNMENT.md"


def score(
    data: dict[str, Any] | None = None,
    *,
    now: dt.datetime | None = None,
    alignment_path: Path = DEFAULT_ALIGNMENT,
) -> dict[str, Any]:
    current = now or dt.datetime.now(dt.timezone.utc)
    corrections = rows_for(data, "corrections")
    ops_rows = rows_for(data, "ops_ledger")
    if corrections:
        correction_rate = per_day(corrections, "created_at", days=7, now=current)
    else:
        correction_rate = 0.0
    if data and data.get("alignment_modified_at"):
        staleness = age_days(data.get("alignment_modified_at"), now=current)
    elif alignment_path.exists():
        modified = dt.datetime.fromtimestamp(alignment_path.stat().st_mtime, tz=dt.timezone.utc)
        staleness = age_days(modified.isoformat(), now=current)
    else:
        staleness = None
    starts = [row for row in ops_rows if row.get("event") == "session_start" or row.get("tag") == "session_start"]
    coherent = sum(1 for row in starts if row.get("coherent") is True or float(row.get("coherence_score") or 0) >= 0.7)
    metrics = {
        "correction_rate": correction_rate,
        "memory_staleness_days": staleness,
        "session_start_coherence": rate(coherent, len(starts)) if starts else 0.0,
    }
    return score_result(
        AGENT,
        primary_metric=correction_rate,
        metrics=metrics,
        trigger_fired=correction_rate > 3.0,
        trigger_metric="correction_rate" if correction_rate > 3.0 else None,
        trigger_reason=f"7d correction rate {correction_rate}/day above 3/day" if correction_rate > 3.0 else None,
    )

