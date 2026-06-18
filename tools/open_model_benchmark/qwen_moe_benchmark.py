#!/usr/bin/env python3
"""Qwen3-30B-A3B MoE benchmark against llama3.1:8b.

Default mode is an offline task-pack/scorer. Live local model execution is
explicitly opt-in through ``--run-ollama`` and only calls already-installed
Ollama tags.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from tools.open_model_benchmark import benchmark as base_benchmark


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "qwen3-30b-a3b-moe-benchmark.v1"
DEFAULT_OUTPUT = REPO_ROOT / "core" / "BUILD" / "signals" / "qwen3_30b_a3b_benchmark.json"
DEFAULT_STATE = REPO_ROOT / "core" / "STATE" / "QWEN3_30B_A3B_BENCHMARK.md"

MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "qwen3-30b-a3b": {
        "ollama_ref": "qwen3:30b-a3b",
        "family": "Qwen3 MoE",
        "total_params_b": 30.0,
        "active_params_b": 3.0,
        "role": "candidate",
    },
    "llama3.1-8b": {
        "ollama_ref": "llama3.1:8b",
        "family": "Llama 3.1 dense",
        "total_params_b": 8.0,
        "active_params_b": 8.0,
        "role": "baseline",
    },
}

TASK_CATEGORIES = {
    "buildstream_classification": "Classify repo instructions and cite evidence.",
    "routing_guardrail": "Identify reserved-class or buildstream-safe routing.",
    "proof_synthesis": "Extract intent solved, unlock, proof, and rollback shape.",
    "code_review": "Find concrete risks from a small patch or handoff excerpt.",
}


@dataclasses.dataclass(frozen=True)
class QwenMoeTask:
    task_id: str
    category: str
    source: str
    prompt: str
    expected_terms: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def build_tasks(
    root: Path | str = REPO_ROOT,
    *,
    max_sources: int = 8,
) -> list[dict[str, Any]]:
    """Build a compact task pack from repo-local source documents."""
    repo = Path(root)
    base_tasks = base_benchmark.build_benchmark_tasks(repo, max_sources=max_sources)
    selected = _balanced_base_tasks(base_tasks)
    tasks: list[QwenMoeTask] = []
    for index, task in enumerate(selected):
        category = _category_for(task, index)
        prompt = _task_prompt(category=category, base_prompt=str(task["prompt"]))
        expected_terms = _expected_terms(category, task)
        tasks.append(
            QwenMoeTask(
                task_id=f"qwen-moe-{index + 1:03d}-{category}",
                category=category,
                source=str(task["source"]),
                prompt=prompt,
                expected_terms=expected_terms,
            )
        )
    return [task.to_json() for task in tasks]


def score_responses(tasks: Iterable[dict[str, Any]], responses: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Score candidate and baseline responses with quality and compute metrics."""
    task_by_id = {str(task["task_id"]): task for task in tasks}
    rows: list[dict[str, Any]] = []
    for response in responses:
        model = _normalize_model(str(response.get("model") or ""))
        task_id = str(response.get("task_id") or "").strip()
        answer = str(response.get("response") or response.get("answer") or "").strip()
        if not model or model not in MODEL_PROFILES or task_id not in task_by_id:
            continue
        latency_ms = response.get("latency_ms")
        score = score_single(task_by_id[task_id], answer)
        rows.append(
            {
                "model": model,
                "task_id": task_id,
                "category": task_by_id[task_id]["category"],
                "quality_score": score["quality_score"],
                "term_hits": score["term_hits"],
                "format_hit": score["format_hit"],
                "evidence_hit": score["evidence_hit"],
                "latency_ms": float(latency_ms) if latency_ms is not None else None,
            }
        )

    model_scores = [_aggregate_model(model, rows) for model in MODEL_PROFILES]
    comparison = compare_candidate(model_scores)
    return {
        "schema": SCHEMA,
        "tasks": len(task_by_id),
        "responses_scored": len(rows),
        "models": model_scores,
        "comparison": comparison,
        "response_scores": sorted(rows, key=lambda row: (row["model"], row["task_id"])),
    }


def score_single(task: dict[str, Any], response: str) -> dict[str, Any]:
    """Score one response by required terms, JSON-ish format, and evidence language."""
    lowered = response.lower()
    expected_terms = [str(term).lower() for term in task.get("expected_terms", [])]
    hits = [term for term in expected_terms if term and term in lowered]
    term_rate = len(hits) / len(expected_terms) if expected_terms else 0.0
    format_hit = _looks_structured(response)
    evidence_hit = any(term in lowered for term in ("because", "evidence", "source", "risk", "rollback", "proof"))
    quality = (term_rate * 0.7) + (0.15 if format_hit else 0.0) + (0.15 if evidence_hit else 0.0)
    return {
        "quality_score": round(min(quality, 1.0), 4),
        "term_hits": hits,
        "format_hit": format_hit,
        "evidence_hit": evidence_hit,
    }


def compare_candidate(model_scores: list[dict[str, Any]]) -> dict[str, Any]:
    by_model = {row["model"]: row for row in model_scores}
    qwen = by_model["qwen3-30b-a3b"]
    llama = by_model["llama3.1-8b"]
    quality_delta = round(qwen["quality_score"] - llama["quality_score"], 4)
    latency_ratio = _ratio(qwen["avg_latency_ms"], llama["avg_latency_ms"])
    active_compute_ratio = _ratio(qwen["active_params_b"], llama["active_params_b"])
    live_rows = qwen["responses"] > 0 and llama["responses"] > 0
    qwen_wins_quality = live_rows and quality_delta >= 0.0
    qwen_meets_compute_claim = qwen["active_params_b"] <= 3.5 and qwen["total_params_b"] >= 30.0
    return {
        "status": "scored" if live_rows else "task_pack_only",
        "candidate": "qwen3-30b-a3b",
        "baseline": "llama3.1-8b",
        "quality_delta_vs_llama": quality_delta,
        "latency_ratio_vs_llama": latency_ratio,
        "active_compute_ratio_vs_llama": active_compute_ratio,
        "candidate_meets_claim": bool(qwen_wins_quality and qwen_meets_compute_claim),
        "claim_test": "Pass only if Qwen3-30B-A3B quality >= llama3.1:8b while active_params_b <= 3.5.",
        "authority": "advisory-only; no routing, deploy, model download, training, or spend authority.",
    }


def run_ollama_tasks(
    tasks: Iterable[dict[str, Any]],
    *,
    max_tasks: int = 4,
    timeout_seconds: int = 180,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[dict[str, Any]]:
    """Run a bounded opt-in local Ollama pass for both benchmark models."""
    selected_tasks = list(tasks)[:max_tasks]
    run = runner or subprocess.run
    rows: list[dict[str, Any]] = []
    for model, profile in MODEL_PROFILES.items():
        for task in selected_tasks:
            started = time.monotonic()
            try:
                completed = run(
                    ["ollama", "run", str(profile["ollama_ref"]), str(task["prompt"])],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                response = completed.stdout.strip() if completed.returncode == 0 else completed.stderr.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                response = f"runner_error: {exc}"
            rows.append(
                {
                    "model": model,
                    "task_id": task["task_id"],
                    "response": response,
                    "latency_ms": round((time.monotonic() - started) * 1000, 2),
                    "runner": "ollama",
                    "model_ref": profile["ollama_ref"],
                }
            )
    return rows


def build_report(
    *,
    root: Path | str = REPO_ROOT,
    responses: Iterable[dict[str, Any]] | None = None,
    run_ollama: bool = False,
    max_sources: int = 8,
    max_tasks: int = 4,
) -> dict[str, Any]:
    tasks = build_tasks(root, max_sources=max_sources)
    response_rows = list(responses or [])
    if run_ollama:
        response_rows.extend(run_ollama_tasks(tasks, max_tasks=max_tasks))
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "models": MODEL_PROFILES,
        "task_count": len(tasks),
        "tasks": tasks,
        "mode": "score" if response_rows else "task-pack",
        "guardrails": [
            "offline scorer by default",
            "live Ollama run is opt-in only",
            "no model downloads",
            "no production routing changes",
            "no deploy, push, merge, outreach, secrets, or money movement",
        ],
    }
    if response_rows:
        report["scores"] = score_responses(tasks, response_rows)
    return report


def write_json(data: dict[str, Any], output: Path | str = DEFAULT_OUTPUT) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_markdown(report: dict[str, Any], output: Path | str = DEFAULT_STATE) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Qwen3-30B-A3B MoE Benchmark",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Mode: `{report['mode']}`",
        f"- Tasks: `{report['task_count']}`",
        "- Candidate: `qwen3-30b-a3b` (`qwen3:30b-a3b`, 30B total / 3B active)",
        "- Baseline: `llama3.1-8b` (`llama3.1:8b`, 8B dense)",
        "- Authority: advisory-only; this report does not change routing or deploy models.",
        "",
        "## Result",
    ]
    scores = report.get("scores")
    if not scores:
        lines.extend(
            [
                "",
                "No live responses were scored in this sandbox. The benchmark task pack is ready for server 162 or any local Ollama host with both model tags already installed.",
                "",
                "Run live only when approved from the target host:",
                "",
                "```bash",
                "python3 -B -m tools.open_model_benchmark.qwen_moe_benchmark --run-ollama --max-tasks 8 --output core/BUILD/signals/qwen3_30b_a3b_benchmark.json --state core/STATE/QWEN3_30B_A3B_BENCHMARK.md",
                "```",
            ]
        )
    else:
        comparison = scores["comparison"]
        lines.extend(
            [
                "",
                f"- Status: `{comparison['status']}`",
                f"- Candidate meets claim: `{comparison['candidate_meets_claim']}`",
                f"- Quality delta vs llama: `{comparison['quality_delta_vs_llama']}`",
                f"- Latency ratio vs llama: `{comparison['latency_ratio_vs_llama']}`",
                f"- Active-compute ratio vs llama: `{comparison['active_compute_ratio_vs_llama']}`",
                "",
                "| Model | Responses | Quality | Avg latency ms | Active params B | Quality per active B |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in scores["models"]:
            lines.append(
                f"| `{row['model']}` | {row['responses']} | {row['quality_score']} | "
                f"{row['avg_latency_ms']} | {row['active_params_b']} | {row['quality_per_active_b']} |"
            )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    return base_benchmark.load_jsonl(path)


def _aggregate_model(model: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    profile = MODEL_PROFILES[model]
    model_rows = [row for row in rows if row["model"] == model]
    quality = _avg(row["quality_score"] for row in model_rows)
    latencies = [float(row["latency_ms"]) for row in model_rows if row.get("latency_ms") is not None]
    avg_latency = _avg(latencies) if latencies else None
    active_params = float(profile["active_params_b"])
    return {
        "model": model,
        "role": profile["role"],
        "responses": len(model_rows),
        "quality_score": round(quality, 4),
        "avg_latency_ms": round(avg_latency, 2) if avg_latency is not None else None,
        "total_params_b": profile["total_params_b"],
        "active_params_b": active_params,
        "quality_per_active_b": round(quality / active_params, 4) if active_params else 0.0,
    }


def _balanced_base_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = [task for task in tasks if task.get("round_name") == "two_shot"] or tasks
    return baseline[:8]


def _category_for(task: dict[str, Any], index: int) -> str:
    expected = str(task.get("expected") or "")
    if expected == "doctrine":
        return "routing_guardrail"
    if expected == "buildstream":
        return "buildstream_classification"
    if expected == "learning":
        return "proof_synthesis"
    if expected == "attention":
        return "routing_guardrail"
    return list(TASK_CATEGORIES)[index % len(TASK_CATEGORIES)]


def _task_prompt(*, category: str, base_prompt: str) -> str:
    instruction = TASK_CATEGORIES[category]
    return (
        f"{instruction}\n"
        "Reply as compact JSON with keys: decision, evidence, risk, confidence.\n"
        "Use only the excerpt in the prompt. If evidence is weak, say so.\n\n"
        f"{base_prompt}"
    )


def _expected_terms(category: str, task: dict[str, Any]) -> tuple[str, ...]:
    terms = [str(term) for term in task.get("evidence_terms", []) if str(term)]
    if category == "buildstream_classification":
        terms.extend(["branch", "registry", "tests"])
    elif category == "routing_guardrail":
        terms.extend(["james", "gate", "reserved"])
    elif category == "proof_synthesis":
        terms.extend(["proof", "unlock", "next"])
    elif category == "code_review":
        terms.extend(["risk", "rollback", "evidence"])
    return tuple(dict.fromkeys(term.lower() for term in terms))


def _normalize_model(model: str) -> str:
    normalized = model.strip().lower().replace("_", "-")
    aliases = {
        "qwen": "qwen3-30b-a3b",
        "qwen3": "qwen3-30b-a3b",
        "qwen3:30b-a3b": "qwen3-30b-a3b",
        "qwen3-30b-a3b-moe": "qwen3-30b-a3b",
        "llama": "llama3.1-8b",
        "llama3.1:8b": "llama3.1-8b",
        "llama-3.1-8b": "llama3.1-8b",
    }
    return aliases.get(normalized, normalized)


def _looks_structured(response: str) -> bool:
    stripped = response.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return True
    lowered = stripped.lower()
    return all(key in lowered for key in ("evidence", "confidence"))


def _ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(float(numerator) / float(denominator), 4)


def _avg(values: Iterable[float]) -> float:
    rows = list(values)
    return sum(rows) / len(rows) if rows else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark Qwen3-30B-A3B MoE against llama3.1:8b.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--responses", type=Path, default=None, help="JSONL model responses to score")
    parser.add_argument("--run-ollama", action="store_true", help="opt-in local Ollama execution")
    parser.add_argument("--max-sources", type=int, default=8)
    parser.add_argument("--max-tasks", type=int, default=4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    responses = load_jsonl(args.responses) if args.responses else []
    report = build_report(
        root=args.root,
        responses=responses,
        run_ollama=args.run_ollama,
        max_sources=args.max_sources,
        max_tasks=args.max_tasks,
    )
    write_json(report, args.output)
    write_markdown(report, args.state)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
