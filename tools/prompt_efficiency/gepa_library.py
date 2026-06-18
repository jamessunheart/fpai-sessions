from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from string import Formatter
from typing import Any, Protocol


DEFAULT_REFLECTION_CMD = "claude -p --effort low"
DEFAULT_REFLECTION_MODEL = "claude-p"
DEFAULT_EVAL_MODEL = "ollama/llama3.1:8b"
COMPONENT = "prompt_template"


class GEPAModule(Protocol):
    def optimize(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class TemplateSpec:
    prompt_id: str
    seed_template: str
    adoption_policy: str = "auto"
    max_metric_calls: int = 6
    reflection_model: str = DEFAULT_REFLECTION_MODEL
    eval_model: str = DEFAULT_EVAL_MODEL


@dataclass(frozen=True)
class TemplateEvaluation:
    text: str
    quality: float
    tokens: int
    required_hits: list[str]
    required_misses: list[str]
    forbidden_hits: list[str]
    feedback: str


@dataclass
class EvaluationBatch:
    outputs: list[dict[str, Any]]
    scores: list[float]
    trajectories: list[dict[str, Any]] | None = None
    objective_scores: list[dict[str, float]] | None = None
    num_metric_calls: int | None = None


class SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def import_gepa() -> GEPAModule | None:
    try:
        return import_module("gepa")
    except Exception:
        return None


def package_status(gepa_module: GEPAModule | None = None) -> dict[str, Any]:
    module = gepa_module if gepa_module is not None else import_gepa()
    return {
        "available": module is not None,
        "package": "gepa",
        "install": "pip install gepa",
        "source": "https://github.com/gepa-ai/gepa",
        "license": "MIT",
    }


def flatten_inputs(inputs: dict[str, Any]) -> dict[str, str]:
    score_row = inputs.get("score_row") if isinstance(inputs.get("score_row"), dict) else {}
    flattened: dict[str, str] = {
        "resource_inventory": str(inputs.get("resource_inventory") or ""),
        "blueprint_text": str(inputs.get("blueprint_text") or ""),
        "recent_context": str(inputs.get("recent_context") or ""),
        "signal": str(inputs.get("signal") or ""),
    }
    if isinstance(score_row, dict):
        flattened.update(
            {
                "agent": str(score_row.get("agent") or ""),
                "trigger_metric": str(score_row.get("trigger_metric") or ""),
                "primary_metric": str(score_row.get("primary_metric") or ""),
                "trigger_reason": str(score_row.get("trigger_reason") or "metric trigger fired"),
                "metrics_json": json.dumps(score_row.get("metrics") or {}, sort_keys=True),
            }
        )
    return flattened


def render_template(template: str, inputs: dict[str, Any]) -> str:
    return template.format_map(SafeFormatDict(flatten_inputs(inputs)))


def template_fields(template: str) -> set[str]:
    return {field for _, field, _, _ in Formatter().parse(template) if field}


def token_count(text: str) -> int:
    return len(text.split())


def evaluate_text(text: str, case: dict[str, Any]) -> TemplateEvaluation:
    required = [str(term) for term in case.get("required_terms") or []]
    forbidden = [str(term) for term in case.get("forbidden_terms") or []]
    lower = text.lower()
    required_hits = [term for term in required if term.lower() in lower]
    forbidden_hits = [term for term in forbidden if term.lower() in lower]
    required_score = len(required_hits) / max(1, len(required))
    forbidden_score = 1.0 if not forbidden_hits else 0.0
    field_terms = [f"{{{field}}}" for field in sorted(template_fields(text))]
    placeholder_score = 1.0 if not field_terms else 0.0
    quality = round((required_score * 0.8) + (forbidden_score * 0.15) + (placeholder_score * 0.05), 4)
    missing = [term for term in required if term not in required_hits]
    feedback = (
        f"quality={quality}; tokens={token_count(text)}; "
        f"required_misses={missing}; forbidden_hits={forbidden_hits}"
    )
    return TemplateEvaluation(
        text=text,
        quality=quality,
        tokens=token_count(text),
        required_hits=required_hits,
        required_misses=missing,
        forbidden_hits=forbidden_hits,
        feedback=feedback,
    )


class PromptTemplateAdapter:
    def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        template = candidate[COMPONENT]
        outputs: list[dict[str, Any]] = []
        scores: list[float] = []
        trajectories: list[dict[str, Any]] | None = [] if capture_traces else None
        for case in batch:
            text = render_template(template, case.get("inputs") or {})
            evaluation = evaluate_text(text, case)
            outputs.append(
                {
                    "text": text,
                    "tokens": evaluation.tokens,
                    "required_misses": evaluation.required_misses,
                    "forbidden_hits": evaluation.forbidden_hits,
                }
            )
            scores.append(evaluation.quality)
            if trajectories is not None:
                trajectories.append(
                    {
                        "case_id": case.get("id"),
                        "inputs": case.get("inputs") or {},
                        "rendered": text,
                        "feedback": evaluation.feedback,
                        "score": evaluation.quality,
                    }
                )
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajectories, num_metric_calls=len(batch))

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        trajectories = eval_batch.trajectories or []
        records = [
            {
                "Inputs": row["inputs"],
                "Generated Outputs": row["rendered"],
                "Feedback": row["feedback"],
                "Current prompt template": candidate[COMPONENT],
            }
            for row in trajectories
        ]
        return {component: records for component in components_to_update}


def claude_cli_proposer(
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
    *,
    reflection_cmd: str | None = None,
) -> dict[str, str]:
    cmd = shlex.split(reflection_cmd or os.environ.get("GEPA_REFLECTION_CMD", DEFAULT_REFLECTION_CMD))
    prompt = (
        "Improve this prompt template for token efficiency while preserving every safety boundary, "
        "required placeholder, and required output contract. Return only the revised template.\n\n"
        f"Current template:\n{candidate[COMPONENT]}\n\n"
        f"Reflection dataset:\n{json.dumps(reflective_dataset, indent=2, sort_keys=True)[:12000]}\n"
    )
    completed = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"GEPA reflection failed: {completed.stderr.strip()[:500]}")
    proposed = completed.stdout.strip()
    if not proposed:
        raise RuntimeError("GEPA reflection returned an empty template")
    return {component: proposed for component in components_to_update}


def baseline_template_result(spec: TemplateSpec, cases: list[dict[str, Any]]) -> dict[str, Any]:
    adapter = PromptTemplateAdapter()
    batch = adapter.evaluate(cases, {COMPONENT: spec.seed_template})
    tokens = [int(output["tokens"]) for output in batch.outputs]
    return {
        "variant_id": "baseline",
        "description": "Current prompt template before GEPA optimization.",
        "quality": round(sum(batch.scores) / max(1, len(batch.scores)), 4),
        "avg_tokens": round(sum(tokens) / max(1, len(tokens)), 2),
        "cases": [
            {
                "case_id": case.get("id") or f"case-{idx + 1}",
                "quality": batch.scores[idx],
                "tokens": tokens[idx],
                "required_misses": batch.outputs[idx]["required_misses"],
                "forbidden_hits": batch.outputs[idx]["forbidden_hits"],
            }
            for idx, case in enumerate(cases)
        ],
    }


def optimize_template(
    spec: TemplateSpec,
    cases: list[dict[str, Any]],
    *,
    gepa_module: GEPAModule | None = None,
    proposer: Any | None = None,
    run_dir: Path | None = None,
) -> dict[str, Any]:
    if os.environ.get("GEPA_OPTIMIZE_DISABLE") == "1":
        return {"status": "disabled", "reason": "GEPA_OPTIMIZE_DISABLE=1"}
    module = gepa_module if gepa_module is not None else import_gepa()
    if module is None:
        return {"status": "unavailable", "reason": "gepa package is not installed"}
    active_proposer = proposer or claude_cli_proposer
    try:
        result = module.optimize(
            seed_candidate={COMPONENT: spec.seed_template},
            trainset=cases,
            valset=cases,
            adapter=PromptTemplateAdapter(),
            custom_candidate_proposer=active_proposer,
            max_metric_calls=spec.max_metric_calls,
            run_dir=str(run_dir) if run_dir else None,
            display_progress_bar=False,
            acceptance_criterion="improvement_or_equal",
            raise_on_exception=True,
        )
    except TypeError as exc:
        return {"status": "unavailable", "reason": f"gepa optimize signature mismatch: {exc}"}
    best_candidate = dict(result.best_candidate)
    best_template = str(best_candidate.get(COMPONENT) or spec.seed_template)
    adapter = PromptTemplateAdapter()
    best_batch = adapter.evaluate(cases, {COMPONENT: best_template})
    tokens = [int(output["tokens"]) for output in best_batch.outputs]
    baseline = baseline_template_result(spec, cases)
    winner = {
        "variant_id": "gepa_best",
        "description": "Best prompt template returned by the real GEPA optimizer.",
        "quality": round(sum(best_batch.scores) / max(1, len(best_batch.scores)), 4),
        "avg_tokens": round(sum(tokens) / max(1, len(tokens)), 2),
        "candidate": best_template,
        "cases": [
            {
                "case_id": case.get("id") or f"case-{idx + 1}",
                "quality": best_batch.scores[idx],
                "tokens": tokens[idx],
                "required_misses": best_batch.outputs[idx]["required_misses"],
                "forbidden_hits": best_batch.outputs[idx]["forbidden_hits"],
            }
            for idx, case in enumerate(cases)
        ],
    }
    quality_pass = winner["quality"] >= baseline["quality"]
    compression_pass = winner["avg_tokens"] < baseline["avg_tokens"]
    return {
        "status": "optimized",
        "engine": "gepa",
        "reflection_model": spec.reflection_model,
        "eval_model": spec.eval_model,
        "baseline": baseline,
        "winner": winner if quality_pass and compression_pass else baseline,
        "candidate": winner,
        "adopted": bool(quality_pass and compression_pass and spec.adoption_policy == "auto"),
        "pending_approval": bool(quality_pass and compression_pass and spec.adoption_policy == "human_approval"),
        "quality_gate": "winner_quality >= baseline_quality",
        "compression_gate": "winner_avg_tokens < baseline_avg_tokens",
        "package": package_status(module),
    }
