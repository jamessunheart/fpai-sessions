#!/usr/bin/env python3
"""Gated GLM-5.2 LoRA fine-tune runner scaffold.

This module prepares a training plan and, only when all gates are explicit,
hands off to a future Unsloth/HuggingFace PEFT training implementation. It is
safe to run on non-GPU hosts: no training starts without FINETUNE_APPROVED=1,
benchmark evidence, HAS_GPU=1, and --execute.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tools.learning import council_guidance, controller

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = Path(os.environ.get("LEARNING_DATASET_OUTPUT", "/opt/fpai-build/learning_datasets/glm52_training.jsonl"))
DEFAULT_OUTPUT_DIR = Path("/opt/fpai-build/models/glm-5.2-fpai-lora")
DEFAULT_BENCHMARK_LEDGER = REPO_ROOT / "core" / "benchmarks" / "per_agent_scores.jsonl"
DEFAULT_READY_NOTICE = Path(os.environ.get("LEARNING_READY_NOTICE", "/opt/fpai-build/learning_datasets/glm52_ready_to_train.json"))
DEFAULT_SIGNAL_LEDGER = controller.DEFAULT_SIGNAL_LEDGER
DEFAULT_DIRECTIVE = council_guidance.DEFAULT_DIRECTIVE_PATH
DEFAULT_MODEL_VERSION = Path(os.environ.get("LEARNING_MODEL_VERSION_LOG", "/opt/fpai-build/learning_datasets/model_versions.jsonl"))

MODEL_NAME = "THUDM/GLM-5.2"
LORA_CONFIG = {"rank": 16, "target_modules": ["q_proj", "v_proj"], "epochs": 3}
MIN_EXAMPLES = 50
MIN_CORRECTIONS = 50
MIN_SIGNALS = 100
RUNPOD_MONTHLY_LIMIT_USD = 50.0


def dataset_stats(path: Path | str) -> dict[str, int]:
    dataset = Path(path)
    if not dataset.exists():
        return {"examples": 0, "corrections": 0}
    examples = 0
    corrections = 0
    with dataset.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            examples += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("source") == "brain_index.corrections":
                corrections += 1
    return {"examples": examples, "corrections": corrections}


def count_jsonl(path: Path | str) -> int:
    return dataset_stats(path)["examples"]


def benchmarks_live(path: Path | str = DEFAULT_BENCHMARK_LEDGER) -> bool:
    ledger = Path(path)
    return ledger.exists() and bool(ledger.read_text(encoding="utf-8").strip())


def has_gpu() -> bool:
    return os.environ.get("HAS_GPU") == "1"


def fine_tune_approved() -> bool:
    return os.environ.get("FINETUNE_APPROVED") == "1"


def runpod_monthly_budget_ok(projected_usd: float | None = None) -> bool:
    if os.environ.get("RUNPOD_BUDGET_MONTHLY_USD") == "0":
        return False
    try:
        limit = float(os.environ.get("RUNPOD_BUDGET_MONTHLY_USD", str(RUNPOD_MONTHLY_LIMIT_USD)))
    except ValueError:
        limit = RUNPOD_MONTHLY_LIMIT_USD
    if projected_usd is None:
        try:
            projected_usd = float(os.environ.get("RUNPOD_PROJECTED_MONTHLY_USD", "0"))
        except ValueError:
            projected_usd = 0.0
    return limit > 0 and projected_usd <= limit


def load_signal_rows(path: Path | str = DEFAULT_SIGNAL_LEDGER) -> list[dict[str, Any]]:
    ledger = Path(path)
    if not ledger.exists():
        return []
    rows: list[dict[str, Any]] = []
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def build_weighted_corpus(
    signal_rows: list[dict[str, Any]],
    directive: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    weights = (directive or {}).get("weighting") or {}
    corpus: list[dict[str, Any]] = []
    for row in signal_rows:
        prompt = str(row.get("prompt") or "").strip()
        response = str(row.get("response") or "").strip()
        signal_type = str(row.get("signal_type") or "").strip()
        if not prompt or not response or signal_type not in controller.VALID_SIGNAL_TYPES:
            continue
        base_weight = float(row.get("weight") or 1.0)
        directive_weight = float(weights.get(signal_type, 1.0))
        corpus.append(
            {
                "prompt": prompt,
                "response": response,
                "signal_type": signal_type,
                "value": float(row.get("value") or 0.0),
                "weight": round(base_weight * directive_weight, 4),
            }
        )
    return corpus


def build_plan(
    *,
    dataset: Path = DEFAULT_DATASET,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    benchmark_ledger: Path = DEFAULT_BENCHMARK_LEDGER,
    signal_ledger: Path = DEFAULT_SIGNAL_LEDGER,
    directive_path: Path = DEFAULT_DIRECTIVE,
    runpod_projected_monthly_usd: float | None = None,
) -> dict[str, Any]:
    stats = dataset_stats(dataset)
    signal_count = controller.count_signals(path=signal_ledger)
    directive = council_guidance.load_directive(directive_path) if Path(directive_path).exists() else {}
    weighted_corpus = build_weighted_corpus(load_signal_rows(signal_ledger), directive)
    gates = {
        "learning_enabled": controller.learning_enabled(),
        "learning_signals": signal_count,
        "min_signals_met": signal_count >= MIN_SIGNALS,
        "dataset_exists": Path(dataset).exists(),
        "dataset_examples": stats["examples"],
        "dataset_corrections": stats["corrections"],
        "min_examples_met": stats["examples"] >= MIN_EXAMPLES,
        "min_corrections_met": stats["corrections"] >= MIN_CORRECTIONS,
        "weighting_directive_exists": bool(directive),
        "weighted_corpus_rows": len(weighted_corpus),
        "d073_benchmarks_live": benchmarks_live(benchmark_ledger),
        "finetune_approved": fine_tune_approved(),
        "has_gpu": has_gpu(),
        "runpod_monthly_budget_ok": runpod_monthly_budget_ok(runpod_projected_monthly_usd),
    }
    ready = bool(
        gates["learning_enabled"]
        and gates["min_signals_met"]
        and gates["dataset_exists"]
        and gates["min_examples_met"]
        and gates["min_corrections_met"]
        and gates["weighting_directive_exists"]
        and gates["d073_benchmarks_live"]
        and gates["finetune_approved"]
        and gates["has_gpu"]
        and gates["runpod_monthly_budget_ok"]
    )
    return {
        "model": MODEL_NAME,
        "dataset": str(dataset),
        "output_dir": str(output_dir),
        "lora": LORA_CONFIG,
        "signal_ledger": str(signal_ledger),
        "directive": str(directive_path),
        "active_model_after_success": "fpai-llama:v{N}",
        "activation_plan": [
            "submit reviewed QLoRA job to RunPod only after every gate passes",
            "pull completed adapter/weights to the approved model directory",
            "create a canonical Ollama Modelfile and run: ollama create fpai-llama:v{N}",
            "update curator.env OLLAMA_ACTIVE_MODEL=fpai-llama:v{N} only after benchmark improvement is proven",
            "append brain_index.model_versions with version, signal_count, metrics, and directive_id",
        ],
        "gates": gates,
        "ready_to_train": ready,
        "will_train": False,
    }


def write_ready_notice(plan: dict[str, Any], notice_path: Path = DEFAULT_READY_NOTICE) -> Path:
    notice_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **plan,
        "notice": (
            "Dataset is prepared, but training is gated. Set FINETUNE_APPROVED=1, "
            "ensure d073 benchmark scores exist, and run on a GPU host with HAS_GPU=1."
        ),
    }
    notice_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return notice_path


def run_training(plan: dict[str, Any], *, execute: bool) -> dict[str, Any]:
    """Training handoff stub. Keeps the scaffold explicit and non-surprising."""
    if not plan["ready_to_train"]:
        return {**plan, "will_train": False, "status": "blocked_by_gates"}
    if not execute:
        return {**plan, "will_train": False, "status": "ready_requires_execute"}
    try:
        import peft  # noqa: F401  # type: ignore
        import transformers  # noqa: F401  # type: ignore
    except ImportError as exc:
        return {**plan, "will_train": False, "status": "missing_training_dependencies", "error": str(exc)}
    return {
        **plan,
        "will_train": False,
        "status": "training_adapter_not_implemented",
        "reason": "Scaffold verified gates/dependencies; reviewed implementation still needed before live GPU execution.",
    }


def record_model_version(
    version: str,
    *,
    signal_count: int,
    metrics: dict[str, Any],
    directive_id: int | None = None,
    path: Path | str = DEFAULT_MODEL_VERSION,
) -> Path:
    row = {
        "version": version,
        "signal_count": signal_count,
        "metrics": metrics,
        "directive_id": directive_id,
        "trained_at": "pending-live-training",
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan or run gated GLM-5.2 LoRA fine-tuning.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--benchmark-ledger", type=Path, default=DEFAULT_BENCHMARK_LEDGER)
    parser.add_argument("--signal-ledger", type=Path, default=DEFAULT_SIGNAL_LEDGER)
    parser.add_argument("--directive", type=Path, default=DEFAULT_DIRECTIVE)
    parser.add_argument("--runpod-projected-monthly-usd", type=float)
    parser.add_argument("--notice", type=Path, default=DEFAULT_READY_NOTICE)
    parser.add_argument("--execute", action="store_true", help="Attempt training only after every gate is true")
    args = parser.parse_args(argv)

    plan = build_plan(
        dataset=args.dataset,
        output_dir=args.output_dir,
        benchmark_ledger=args.benchmark_ledger,
        signal_ledger=args.signal_ledger,
        directive_path=args.directive,
        runpod_projected_monthly_usd=args.runpod_projected_monthly_usd,
    )
    result = run_training(plan, execute=args.execute)
    if result["status"] != "ready_requires_execute" and not result.get("will_train"):
        write_ready_notice(result, args.notice)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"blocked_by_gates", "ready_requires_execute", "missing_training_dependencies"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
