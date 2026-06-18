"""Read-only liveness status summaries from the ops ledger."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def liveness_honest_map_lines(ops_ledger: Path | None = None) -> list[str]:
    ledger = ops_ledger or Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
    if not ledger.exists():
        return []
    latest: dict[str, dict[str, Any]] = {}
    try:
        lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for raw in lines[-500:]:
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        event = str(row.get("event") or "")
        if not event.startswith("liveness:"):
            continue
        ident = str(row.get("spec_id") or "").strip()
        if not ident:
            detail = str(row.get("detail") or "")
            ident = detail.split()[0] if detail.startswith("SPEC_") else ""
        if not ident:
            continue
        status = str(row.get("liveness_status") or "").strip()
        if not status:
            status = {
                "liveness:pass": "live",
                "liveness:partial": "partial",
                "liveness:planned": "planned",
                "liveness:fail": "dead",
            }.get(event, event.removeprefix("liveness:"))
        latest[ident] = {**row, "status": status}
    if not latest:
        return []
    counts = {"live": 0, "partial": 0, "dead": 0, "planned": 0}
    for row in latest.values():
        status = str(row.get("status") or "planned")
        counts[status if status in counts else "partial"] += 1
    lines_out = [
        "Liveness map: "
        f"running={counts['live']} | partial={counts['partial']} | dead={counts['dead']} | planned={counts['planned']}"
    ]
    not_live = [
        (ident, row)
        for ident, row in sorted(latest.items())
        if str(row.get("status")) in {"partial", "dead"}
    ]
    for ident, row in not_live[:3]:
        detail = str(row.get("detail") or "").strip()
        lines_out.append(f"- {ident}: {row.get('status')} · {detail[:140]}")
    return lines_out
