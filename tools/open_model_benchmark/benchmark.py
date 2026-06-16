#!/usr/bin/env python3
"""Benchmark open models on James's repo-local corpus.

This is a scaffold, not a training loop. By default it only builds deterministic
tasks and scores supplied response JSONL. Live model execution is opt-in through
``--run-ollama`` and never downloads models, writes production state, or changes
routing authority.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "core" / "BUILD" / "signals" / "open_model_benchmark.json"
SCHEMA = "open-model-benchmark.v1"

DEFAULT_MODELS = {
    "qwen": "qwen2.5:7b-instruct",
    "mistral": "mistral:7b-instruct",
    "llama": "llama3.1:8b-instruct",
    "gemma": "gemma2:9b-instruct",
}

CORPUS_GLOBS = (
    "docs/codex/*.md",
    "docs/codex/specs/*.md",
    "docs/blueprints/*.md",
    "core/STATE/identity/*.md",
    "core/STATE/*.md",
)
SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__"}

CATEGORIES = {
    "doctrine": ("doctrine", "reserved class", "resource discipline", "self-standing", "rung"),
    "buildstream": ("spec", "branch", "registry", "merge", "tests", "build loop"),
    "attention": ("james", "attention", "coherence", "upstream", "source"),
    "learning": ("feedback", "preference", "learning", "benchmark", "eval", "reviewer"),
    "resources": ("treasury", "cost", "budget", "spend", "subscription", "resource"),
}


@dataclasses.dataclass(frozen=True)
class BenchmarkTask:
    """One corpus-grounded task used across baseline and learning rounds."""

    task_id: str
    source: str
    category: str
    expected: str
    round_name: str
    prompt: str
    evidence_terms: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ModelResponse:
    """One model answer to one benchmark task."""

    model: str
    task_id: str
    response: str
    latency_ms: float | None = None


def build_benchmark_tasks(
    root: Path | str = REPO_ROOT,
    *,
    max_sources: int = 24,
) -> list[dict[str, Any]]:
    """Build deterministic benchmark tasks from repo-local corpus files."""
    repo = Path(root)
    docs = _collect_corpus_docs(repo, max_sources=max_sources)
    tasks: list[BenchmarkTask] = []
    examples = _few_shot_examples()
    for path, text in docs:
        category, terms = classify_text(text)
        excerpt = _excerpt(text, terms)
        expected = category
        for round_name in ("baseline", "one_shot", "two_shot"):
            prompt = _task_prompt(excerpt, round_name=round_name, examples=examples)
            tasks.append(
                BenchmarkTask(
                    task_id=_task_id(path, round_name, expected, prompt),
                    source=str(path.relative_to(repo)),
                    category=category,
                    expected=expected,
                    round_name=round_name,
                    prompt=prompt,
                    evidence_terms=tuple(terms[:3]),
                )
            )
    return [task.to_json() for task in sorted(tasks, key=lambda item: item.task_id)]


def score_responses(tasks: Iterable[dict[str, Any]], responses: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Score model responses and return aggregate metrics plus role assignments."""
    task_by_id = {str(task["task_id"]): task for task in tasks}
    rows: list[dict[str, Any]] = []
    for response in responses:
        parsed = _parse_response(response)
        task = task_by_id.get(parsed.task_id)
        if not task:
            continue
        score = score_single_response(task, parsed.response)
        rows.append(
            {
                "model": parsed.model,
                "task_id": parsed.task_id,
                "round": task["round_name"],
                "source": task["source"],
                "expected": task["expected"],
                "score": score["score"],
                "category_hit": score["category_hit"],
                "evidence_hit": score["evidence_hit"],
                "calibration_hit": score["calibration_hit"],
                "latency_ms": parsed.latency_ms,
            }
        )

    models = sorted({row["model"] for row in rows})
    aggregates = [_aggregate_model(model, [row for row in rows if row["model"] == model]) for model in models]
    return {
        "schema": SCHEMA,
        "tasks": len(task_by_id),
        "responses_scored": len(rows),
        "models": aggregates,
        "cooperative_setup": assign_cooperative_roles(aggregates),
        "response_scores": sorted(rows, key=lambda row: (row["model"], row["task_id"])),
    }


def score_single_response(task: dict[str, Any], response: str) -> dict[str, Any]:
    """Score one answer against a category task.

    Expected answer is the category label. Extra credit goes to evidence terms
    and calibrated uncertainty language, which makes the same response useful
    for reviewer specialization.
    """
    lowered = response.lower()
    expected = str(task["expected"]).lower()
    evidence_terms = [str(term).lower() for term in task.get("evidence_terms", [])]
    category_hit = expected in lowered
    evidence_hit = any(term and term in lowered for term in evidence_terms)
    calibration_hit = any(term in lowered for term in ("because", "evidence", "uncertain", "confidence", "source"))
    score = 0.0
    if category_hit:
        score += 0.72
    if evidence_hit:
        score += 0.18
    if calibration_hit:
        score += 0.10
    return {
        "score": round(min(score, 1.0), 4),
        "category_hit": category_hit,
        "evidence_hit": evidence_hit,
        "calibration_hit": calibration_hit,
    }


def assign_cooperative_roles(model_scores: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Assign builder/reviewer roles and cross-check pairings from metrics."""
    models = sorted(model_scores, key=lambda row: str(row.get("model", "")))
    ranked_builders = sorted(models, key=lambda row: (-float(row.get("builder_score", 0)), str(row.get("model", ""))))
    ranked_reviewers = sorted(models, key=lambda row: (-float(row.get("reviewer_score", 0)), str(row.get("model", ""))))
    builder = ranked_builders[0]["model"] if ranked_builders else None
    reviewer = next((row["model"] for row in ranked_reviewers if row.get("model") != builder), None)
    if reviewer is None and ranked_reviewers:
        reviewer = ranked_reviewers[0]["model"]

    specialists = []
    for row in models:
        model = row["model"]
        if model == builder:
            role = "builder"
        elif model == reviewer:
            role = "reviewer"
        else:
            role = "specialist"
        specialists.append(
            {
                "model": model,
                "role": role,
                "builder_score": row.get("builder_score", 0),
                "reviewer_score": row.get("reviewer_score", 0),
                "learning_gain": row.get("learning_gain", 0),
            }
        )

    pairings = []
    if builder and reviewer and builder != reviewer:
        pairings.append(
            {
                "builder": builder,
                "reviewer": reviewer,
                "protocol": "builder drafts from corpus task; reviewer must cite source evidence and veto unsupported claims",
            }
        )
    for row in ranked_builders[:2]:
        for other in ranked_reviewers[:2]:
            if row.get("model") != other.get("model"):
                pair = {
                    "builder": row["model"],
                    "reviewer": other["model"],
                    "protocol": "cross-check one held-out task before adopting the answer",
                }
                if pair not in pairings:
                    pairings.append(pair)
    return {
        "authority": "advisory-only",
        "builder": builder,
        "reviewer": reviewer,
        "specialists": specialists,
        "cross_checks": pairings,
        "gate": "No model may self-promote, train, deploy, spend, send outreach, or alter routing from this benchmark.",
    }


def run_ollama_tasks(
    tasks: Iterable[dict[str, Any]],
    *,
    models: dict[str, str] | None = None,
    max_tasks: int = 4,
    timeout_seconds: int = 120,
) -> list[dict[str, Any]]:
    """Run a small opt-in Ollama benchmark and return response rows."""
    selected_models = models or DEFAULT_MODELS
    selected_tasks = list(tasks)[:max_tasks]
    rows: list[dict[str, Any]] = []
    for model_name, ollama_name in selected_models.items():
        for task in selected_tasks:
            start = time.monotonic()
            try:
                completed = subprocess.run(
                    ["ollama", "run", ollama_name, str(task["prompt"])],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                latency_ms = (time.monotonic() - start) * 1000
                response = completed.stdout.strip() if completed.returncode == 0 else completed.stderr.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                latency_ms = (time.monotonic() - start) * 1000
                response = f"runner_error: {exc}"
            rows.append(
                {
                    "model": model_name,
                    "task_id": task["task_id"],
                    "response": response,
                    "latency_ms": round(latency_ms, 2),
                    "runner": "ollama",
                    "model_ref": ollama_name,
                }
            )
    return rows


def write_json(data: dict[str, Any], output: Path | str = DEFAULT_OUTPUT) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}") from exc
            if isinstance(item, dict):
                rows.append(item)
    return rows


def classify_text(text: str) -> tuple[str, list[str]]:
    lowered = text.lower()
    scored: list[tuple[int, str, list[str]]] = []
    for category, terms in CATEGORIES.items():
        hits = [term for term in terms if term in lowered]
        scored.append((len(hits), category, hits or [terms[0]]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][1], scored[0][2]


def _collect_corpus_docs(repo: Path, *, max_sources: int) -> list[tuple[Path, str]]:
    docs: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    for pattern in CORPUS_GLOBS:
        for path in sorted(repo.glob(pattern)):
            if len(docs) >= max_sources:
                return docs
            if path in seen or any(part in SKIP_PARTS for part in path.parts) or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if len(text.strip()) < 80:
                continue
            seen.add(path)
            docs.append((path, text))
    return docs


def _task_prompt(excerpt: str, *, round_name: str, examples: str) -> str:
    base = (
        "Classify the corpus excerpt into exactly one label: doctrine, buildstream, "
        "attention, learning, resources. Reply as JSON with keys label, evidence, confidence.\n\n"
    )
    if round_name == "one_shot":
        base += examples.split("\n\n")[0] + "\n\n"
    elif round_name == "two_shot":
        base += examples + "\n\n"
    return base + f"Excerpt:\n{excerpt}\n"


def _few_shot_examples() -> str:
    return (
        'Example: "Branch off feat/headless-build, register in REGISTRY, run tests."\n'
        '{"label":"buildstream","evidence":"branch/register/tests","confidence":0.86}\n\n'
        'Example: "James stays upstream; AI routes downstream and protects coherence."\n'
        '{"label":"attention","evidence":"James/upstream/coherence","confidence":0.88}'
    )


def _excerpt(text: str, terms: list[str]) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    lowered = clean.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    start = max(0, min(positions) - 260) if positions else 0
    return clean[start : start + 900]


def _task_id(path: Path, round_name: str, expected: str, prompt: str) -> str:
    digest = hashlib.sha256(f"{path}:{round_name}:{expected}:{prompt}".encode("utf-8")).hexdigest()
    return f"omb-{digest[:16]}"


def _parse_response(item: dict[str, Any]) -> ModelResponse:
    model = str(item.get("model") or "").strip().lower()
    task_id = str(item.get("task_id") or "").strip()
    response = str(item.get("response") or item.get("answer") or "").strip()
    if not model or not task_id:
        raise ValueError("response row requires model and task_id")
    latency = item.get("latency_ms")
    return ModelResponse(model=model, task_id=task_id, response=response, latency_ms=float(latency) if latency is not None else None)


def _aggregate_model(model: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "model": model,
            "accuracy": 0.0,
            "baseline_accuracy": 0.0,
            "learning_accuracy": 0.0,
            "learning_gain": 0.0,
            "avg_latency_ms": None,
            "builder_score": 0.0,
            "reviewer_score": 0.0,
        }
    accuracy = _avg(row["score"] for row in rows)
    baseline = _avg(row["score"] for row in rows if row["round"] == "baseline")
    learned = _avg(row["score"] for row in rows if row["round"] in {"one_shot", "two_shot"})
    learning_gain = max(0.0, learned - baseline)
    evidence_rate = _avg(1.0 if row["evidence_hit"] else 0.0 for row in rows)
    calibration_rate = _avg(1.0 if row["calibration_hit"] else 0.0 for row in rows)
    latencies = [float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None]
    avg_latency = _avg(latencies) if latencies else None
    speed_score = 0.5 if avg_latency is None else max(0.0, min(1.0, 1.0 - (avg_latency / 120000.0)))
    builder_score = (accuracy * 0.62) + (learning_gain * 0.23) + (speed_score * 0.15)
    reviewer_score = (accuracy * 0.48) + (evidence_rate * 0.27) + (calibration_rate * 0.25)
    return {
        "model": model,
        "responses": len(rows),
        "accuracy": round(accuracy, 4),
        "baseline_accuracy": round(baseline, 4),
        "learning_accuracy": round(learned, 4),
        "learning_gain": round(learning_gain, 4),
        "evidence_rate": round(evidence_rate, 4),
        "calibration_rate": round(calibration_rate, 4),
        "avg_latency_ms": round(avg_latency, 2) if avg_latency is not None else None,
        "builder_score": round(builder_score, 4),
        "reviewer_score": round(reviewer_score, 4),
    }


def _avg(values: Iterable[float]) -> float:
    rows = list(values)
    if not rows:
        return 0.0
    return sum(rows) / len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and score the open-model benchmark scaffold.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=None, help="optional JSON report output path")
    parser.add_argument("--responses", type=Path, default=None, help="JSONL model responses to score")
    parser.add_argument("--run-ollama", action="store_true", help="opt-in local Ollama execution for the first tasks")
    parser.add_argument("--max-sources", type=int, default=24)
    parser.add_argument("--max-tasks", type=int, default=4, help="max tasks per model when --run-ollama is set")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args(argv)

    tasks = build_benchmark_tasks(args.root, max_sources=args.max_sources)
    responses: list[dict[str, Any]] = []
    if args.responses:
        responses.extend(load_jsonl(args.responses))
    if args.run_ollama:
        responses.extend(run_ollama_tasks(tasks, max_tasks=args.max_tasks))

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "model_targets": DEFAULT_MODELS,
        "task_count": len(tasks),
        "tasks": tasks,
        "mode": "score" if responses else "task-pack",
        "guardrails": [
            "advisory-only",
            "no model downloads",
            "no training",
            "no production routing",
            "no spend unless operator intentionally runs local Ollama infrastructure",
        ],
    }
    if responses:
        report["scores"] = score_responses(tasks, responses)

    if args.output:
        write_json(report, args.output)
    if args.json or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
