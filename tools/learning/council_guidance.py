#!/usr/bin/env python3
"""Council-guided weighting directives for model learning cycles."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIRECTIVE_PATH = REPO_ROOT / "core" / "BUILD" / "signals" / "weighting_directive.json"
SIGNAL_TYPES = ("correction", "approval", "reversal", "merge_outcome", "engagement", "council_verdict")
DEFAULT_WEIGHTS = {
    "correction": 1.5,
    "approval": 0.8,
    "reversal": 1.8,
    "merge_outcome": 1.2,
    "engagement": 1.3,
    "council_verdict": 1.0,
}


def produce_weighting_directive(
    *,
    metrics: dict[str, Any] | None = None,
    signal_counts: dict[str, int] | None = None,
    output_path: Path | str = DEFAULT_DIRECTIVE_PATH,
) -> dict[str, Any]:
    """Create a deterministic council-style directive and write it to JSON."""
    metrics = metrics or {}
    signal_counts = signal_counts or {}
    weighting = dict(DEFAULT_WEIGHTS)

    regressions = int(metrics.get("regressions", 0) or 0)
    weak_tasks = int(metrics.get("weak_tasks", 0) or 0)
    engagement_delta = float(metrics.get("engagement_delta", 0.0) or 0.0)
    if regressions:
        weighting["reversal"] = min(3.0, weighting["reversal"] + 0.4)
        weighting["approval"] = max(0.4, weighting["approval"] - 0.2)
    if weak_tasks:
        weighting["correction"] = min(3.0, weighting["correction"] + 0.2)
        weighting["council_verdict"] = min(3.0, weighting["council_verdict"] + 0.2)
    if engagement_delta > 0:
        weighting["engagement"] = min(3.0, weighting["engagement"] + 0.3)
    if signal_counts.get("approval", 0) > signal_counts.get("correction", 0) * 3:
        weighting["approval"] = max(0.4, weighting["approval"] - 0.2)

    directive = {
        "issued_at": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pragmatist_input": "Trust signals that changed outcomes; prioritize weak task classes over applause.",
        "visionary_input": "Develop the model toward clearer routing, fewer James-decision leaks, and better engagement.",
        "skeptic_input": "Watch regressions and over-weighted approvals; reversals and corrections carry higher truth density.",
        "weighting": {key: round(float(weighting[key]), 2) for key in SIGNAL_TYPES},
        "rationale": _rationale(metrics, signal_counts),
        "status": "directive_ready",
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(directive, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return directive


def store_directive(conn: Any, directive: dict[str, Any]) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO brain_index.model_directives
              (pragmatist_input, visionary_input, skeptic_input, weighting, rationale)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                directive["pragmatist_input"],
                directive["visionary_input"],
                directive["skeptic_input"],
                json.dumps(directive["weighting"], sort_keys=True),
                directive["rationale"],
            ),
        )
    finally:
        close = getattr(cur, "close", None)
        if callable(close):
            close()


def load_directive(path: Path | str = DEFAULT_DIRECTIVE_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rationale(metrics: dict[str, Any], signal_counts: dict[str, int]) -> str:
    parts = [
        "corrections and reversals remain high-weight because they expose concrete model error",
        "approval is useful but discounted unless paired with downstream proof",
    ]
    if metrics.get("regressions"):
        parts.append("regressions were reported, so reversal weight increased")
    if metrics.get("weak_tasks"):
        parts.append("weak task classes were reported, so correction and council-verdict weight increased")
    if signal_counts:
        parts.append(f"signal counts reviewed: {json.dumps(signal_counts, sort_keys=True)}")
    return "; ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produce a model weighting directive.")
    parser.add_argument("--metrics", type=Path, help="Optional JSON metrics with regressions/weak_tasks/engagement_delta")
    parser.add_argument("--signal-counts", type=Path, help="Optional JSON object of signal counts")
    parser.add_argument("--output", type=Path, default=DEFAULT_DIRECTIVE_PATH)
    args = parser.parse_args(argv)

    metrics = json.loads(args.metrics.read_text(encoding="utf-8")) if args.metrics else {}
    signal_counts = json.loads(args.signal_counts.read_text(encoding="utf-8")) if args.signal_counts else {}
    directive = produce_weighting_directive(metrics=metrics, signal_counts=signal_counts, output_path=args.output)
    print(json.dumps(directive, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
