#!/usr/bin/env python3
"""Evaluate a preference judge against the frozen held-out split.

The CLI prints one number: judge accuracy minus baseline accuracy. Positive is
go, zero or negative is no-go. This is advisory shadow measurement only.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.learn.build_preference_dataset import load_jsonl

JudgeFn = Callable[[dict[str, Any]], str]


def eval_judge(rows: list[dict[str, Any]], judge_fn: JudgeFn, *, baseline_fn: JudgeFn | None = None) -> float:
    """Return the go/no-go number: judge accuracy minus baseline accuracy."""
    heldout = [row for row in rows if row.get("split") == "eval" and row.get("never_train") is True and row.get("eval")]
    if not heldout:
        return 0.0
    baseline_fn = baseline_fn or baseline_predict
    judge_accuracy = _accuracy(heldout, judge_fn)
    baseline_accuracy = _accuracy(heldout, baseline_fn)
    return judge_accuracy - baseline_accuracy


def baseline_predict(row: dict[str, Any]) -> str:
    """Deterministic baseline: always choose candidate A."""
    return "A"


def keyword_judge(row: dict[str, Any]) -> str:
    """Tiny built-in smoke-test judge; not intended as a real model."""
    candidate_a = row["eval"].get("A", "").lower()
    candidate_b = row["eval"].get("B", "").lower()
    good_words = ("proof", "tested", "reversible", "guard", "receipt", "correction", "realized")
    bad_words = ("regressed", "failed", "missing", "broke", "unsafe", "stale")
    score_a = sum(word in candidate_a for word in good_words) - sum(word in candidate_a for word in bad_words)
    score_b = sum(word in candidate_b for word in good_words) - sum(word in candidate_b for word in bad_words)
    return "B" if score_b > score_a else "A"


def load_judge(spec: str) -> JudgeFn:
    """Load ``module:function`` or a built-in judge name."""
    if spec == "baseline":
        return baseline_predict
    if spec == "keyword":
        return keyword_judge
    if ":" not in spec:
        raise ValueError("judge must be 'baseline', 'keyword', or 'module:function'")
    module_name, function_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, function_name)
    if not callable(fn):
        raise ValueError(f"judge is not callable: {spec}")
    return fn


def _accuracy(rows: list[dict[str, Any]], judge_fn: JudgeFn) -> float:
    correct = 0
    for row in rows:
        public_row = _public_eval_row(row)
        prediction = _normalize_prediction(judge_fn(public_row))
        if prediction == row["eval"]["label"]:
            correct += 1
    return correct / len(rows)


def _public_eval_row(row: dict[str, Any]) -> dict[str, Any]:
    public = dict(row)
    eval_view = dict(public["eval"])
    eval_view.pop("label", None)
    public["eval"] = eval_view
    public.pop("preferred", None)
    public.pop("rejected", None)
    return public


def _normalize_prediction(value: Any) -> str:
    text = str(value).strip().upper()
    if text in {"A", "B"}:
        return text
    if text in {"PREFERRED", "1", "TRUE"}:
        return "A"
    if text in {"REJECTED", "0", "FALSE"}:
        return "B"
    raise ValueError(f"judge returned unsupported prediction: {value!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print one go/no-go number for a held-out preference judge.")
    parser.add_argument("dataset", type=Path, help="Preference JSONL dataset")
    parser.add_argument("--judge", default="keyword", help="'baseline', 'keyword', or 'module:function'")
    args = parser.parse_args(argv)

    number = eval_judge(load_jsonl(args.dataset), load_judge(args.judge))
    print(f"{number:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

