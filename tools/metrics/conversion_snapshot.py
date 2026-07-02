#!/usr/bin/env python3
"""Minimal conversion-metrics snapshot — unblocks d131 nightly metabolism.

Writes ~/.config/fpai/metrics/conversion_latest.json from live sources:
awareness reliability (ops_ledger), build-queue drain (brain_index), and
commit cadence (git). This is the smallest real implementation of the d130
role; the full conversion-metric ledger can replace it when it merges.

Read-only against its sources; writes only the snapshot file.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
OUT_PATH = Path(os.environ.get("FPAI_CONVERSION_LATEST", "~/.config/fpai/metrics/conversion_latest.json")).expanduser()


def awareness_reliability(ledger: Path = OPS_LEDGER) -> dict | None:
    """Latest cumulative probe reliability from ops_ledger."""
    try:
        lines = ledger.read_text(errors="ignore").splitlines()
    except OSError:
        return None
    for line in reversed(lines[-2000:]):
        if "awareness_reliability_probe" not in line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rel = row.get("reliability")
        if rel is None:
            continue
        return {
            "name": "bot_awareness_reliability",
            "value": float(rel),
            "target": float(row.get("threshold") or 0.95),
            "higher_is_better": True,
            "source": str(ledger),
            "detail": f"successes={row.get('successes')} total={row.get('total')} at {row.get('ts')}",
        }
    return None


def pipeline_drain(db_url: str | None = None) -> dict | None:
    """Share of answered decisions that reached merged (pipeline conversion)."""
    db_url = db_url or os.environ.get("BRAIN_INDEX_DB_URL", "")
    if not db_url:
        return None
    try:
        import psycopg

        with psycopg.connect(db_url) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FILTER (WHERE build_status='merged'),"
                " count(*) FROM brain_index.decisions"
                " WHERE status='answered' AND needs_build"
            )
            merged, total = cur.fetchone()
    except Exception:
        return None
    if not total:
        return None
    return {
        "name": "spec_merge_conversion",
        "value": merged / total,
        "target": 0.9,
        "higher_is_better": True,
        "source": "brain_index.decisions",
        "detail": f"merged={merged} answered={total}",
    }


def active_days_share(repo: Path = REPO_ROOT, window_days: int = 14) -> dict | None:
    """Share of the last N days with at least one commit — the dead-days metric."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "log", f"--since={window_days} days ago", "--format=%ad", "--date=short"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    days = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return {
        "name": "active_days_share",
        "value": len(days) / window_days,
        "target": 1.0,
        "higher_is_better": True,
        "source": "git log",
        "detail": f"{len(days)}/{window_days} days with commits",
    }


def build_snapshot() -> dict:
    conversions = [c for c in (awareness_reliability(), pipeline_drain(), active_days_share()) if c]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generator": "tools/metrics/conversion_snapshot.py (minimal d130 stand-in)",
        "conversions": conversions,
    }


def main() -> int:
    snapshot = build_snapshot()
    if not snapshot["conversions"]:
        print(json.dumps({"ok": False, "reason": "no conversions measurable"}))
        return 1
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(snapshot, indent=2))
    print(json.dumps({"ok": True, "path": str(OUT_PATH), "count": len(snapshot["conversions"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
