from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tools.benchmarks import REPO_ROOT, load_json

PROMPT_ID_BENCHMARK_IMPROVEMENT = "benchmark_improvement_spec"
DEFAULT_CASES = REPO_ROOT / "core" / "benchmarks" / "prompt_efficiency_cases.json"
DEFAULT_ADOPTIONS = REPO_ROOT / "core" / "benchmarks" / "prompt_efficiency_adoptions.json"
DEFAULT_REPORT_JSON = REPO_ROOT / "core" / "BUILD" / "signals" / "prompt_efficiency.json"
DEFAULT_REPORT_MD = REPO_ROOT / "core" / "BUILD" / "signals" / "prompt_efficiency.md"
DEFAULT_STATE_MD = REPO_ROOT / "core" / "STATE" / "PROMPT_EFFICIENCY.md"


@dataclass(frozen=True)
class Variant:
    prompt_id: str
    variant_id: str
    renderer: Callable[[dict[str, Any]], str]
    description: str


def utc_stamp(now: dt.datetime | None = None) -> str:
    current = now or dt.datetime.now(dt.timezone.utc)
    return current.strftime("%Y-%m-%dT%H:%M:%SZ")


def token_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _score_row(inputs: dict[str, Any]) -> dict[str, Any]:
    row = inputs.get("score_row") or {}
    return row if isinstance(row, dict) else {}


def render_benchmark_improvement_baseline(inputs: dict[str, Any]) -> str:
    score_row = _score_row(inputs)
    agent = score_row.get("agent")
    metric = score_row.get("trigger_metric")
    value = score_row.get("primary_metric")
    reason = score_row.get("trigger_reason") or "metric trigger fired"
    resource_inventory = str(inputs.get("resource_inventory") or "")
    blueprint_text = str(inputs.get("blueprint_text") or "")
    recent_context = str(inputs.get("recent_context") or "")
    return (
        "Draft one concise repo-build improvement spec for the FPAI agent below.\n"
        "Return markdown only. Do not request production deploys, outreach sends, secrets, money movement, or irreversible actions.\n\n"
        f"Agent: {agent}\n"
        f"Triggered metric: {metric}\n"
        f"Current value: {value}\n"
        f"Reason: {reason}\n"
        f"Metrics JSON: {json.dumps(score_row.get('metrics') or {}, sort_keys=True)}\n\n"
        "Available resources on server 162:\n"
        f"{resource_inventory[:24000]}\n\n"
        "Use those existing CLIs, Python libraries, configured API names, or local scripts when relevant. "
        "Do not request secret values or duplicate installed tools.\n\n"
        f"Blueprint:\n{blueprint_text[:4000]}\n\n"
        f"Recent related context:\n{recent_context[:2000]}\n"
    )


def render_benchmark_improvement_compressed_guarded(inputs: dict[str, Any]) -> str:
    score_row = _score_row(inputs)
    agent = score_row.get("agent")
    metric = score_row.get("trigger_metric")
    value = score_row.get("primary_metric")
    reason = score_row.get("trigger_reason") or "metric trigger fired"
    resource_inventory = str(inputs.get("resource_inventory") or "")
    blueprint_text = str(inputs.get("blueprint_text") or "")
    recent_context = str(inputs.get("recent_context") or "")
    return (
        "Draft one concise repo-build improvement spec for this FPAI agent. Return markdown only.\n"
        "Safety: no production deploys, outreach sends, secrets, money movement, or irreversible actions.\n"
        f"Agent: {agent}\n"
        f"Metric: {metric}; value: {value}; reason: {reason}\n"
        f"Metrics JSON: {json.dumps(score_row.get('metrics') or {}, sort_keys=True)}\n"
        "Available resources on server 162 (reuse; Do not request secret values or duplicate installed tools):\n"
        f"{resource_inventory[:24000]}\n"
        f"Blueprint:\n{blueprint_text[:4000]}\n"
        f"Recent related context:\n{recent_context[:2000]}\n"
    )


def render_benchmark_improvement_compressed_sparse(inputs: dict[str, Any]) -> str:
    score_row = _score_row(inputs)
    return (
        "Draft a repo improvement spec.\n"
        f"Agent: {score_row.get('agent')}\n"
        f"Metric: {score_row.get('trigger_metric')}={score_row.get('primary_metric')}\n"
        f"Context:\n{str(inputs.get('recent_context') or '')[:1200]}\n"
    )


def render_benchmark_improvement_no_resource_gate(inputs: dict[str, Any]) -> str:
    score_row = _score_row(inputs)
    return (
        "Draft one concise repo-build improvement spec. Return markdown only.\n"
        "Safety: no production deploys, outreach sends, secrets, money movement, or irreversible actions.\n"
        f"Agent: {score_row.get('agent')}\n"
        f"Metric: {score_row.get('trigger_metric')}; value: {score_row.get('primary_metric')}\n"
        f"Metrics JSON: {json.dumps(score_row.get('metrics') or {}, sort_keys=True)}\n"
        f"Blueprint:\n{str(inputs.get('blueprint_text') or '')[:4000]}\n"
        f"Recent related context:\n{str(inputs.get('recent_context') or '')[:2000]}\n"
    )


VARIANTS: dict[str, list[Variant]] = {
    PROMPT_ID_BENCHMARK_IMPROVEMENT: [
        Variant(
            PROMPT_ID_BENCHMARK_IMPROVEMENT,
            "baseline",
            render_benchmark_improvement_baseline,
            "Current benchmark improvement proposer prompt.",
        ),
        Variant(
            PROMPT_ID_BENCHMARK_IMPROVEMENT,
            "compressed_guarded",
            render_benchmark_improvement_compressed_guarded,
            "GEPA candidate: compact layout retaining safety, resource, metrics, blueprint, and recent-context genes.",
        ),
        Variant(
            PROMPT_ID_BENCHMARK_IMPROVEMENT,
            "compressed_sparse",
            render_benchmark_improvement_compressed_sparse,
            "GEPA candidate: aggressive compression expected to fail contract coverage.",
        ),
        Variant(
            PROMPT_ID_BENCHMARK_IMPROVEMENT,
            "compressed_no_resource_gate",
            render_benchmark_improvement_no_resource_gate,
            "GEPA candidate: removes resource-reuse context to test quality guard rejection.",
        ),
    ]
}


def adoption_map(path: Path = DEFAULT_ADOPTIONS) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = load_json(path)
    except (json.JSONDecodeError, OSError):
        return {}
    rows = data.get("adoptions") if isinstance(data, dict) else {}
    if not isinstance(rows, dict):
        return {}
    out: dict[str, str] = {}
    for prompt_id, row in rows.items():
        if isinstance(row, dict) and row.get("variant_id"):
            out[str(prompt_id)] = str(row["variant_id"])
    return out


def variant_for(prompt_id: str, variant_id: str) -> Variant:
    for variant in VARIANTS.get(prompt_id, []):
        if variant.variant_id == variant_id:
            return variant
    raise KeyError(f"unknown prompt variant: {prompt_id}/{variant_id}")


def render_prompt(prompt_id: str, inputs: dict[str, Any], *, adoptions_path: Path = DEFAULT_ADOPTIONS) -> str:
    selected = adoption_map(adoptions_path).get(prompt_id, "baseline")
    try:
        return variant_for(prompt_id, selected).renderer(inputs)
    except KeyError:
        return variant_for(prompt_id, "baseline").renderer(inputs)


def quality_score(text: str, case: dict[str, Any]) -> dict[str, Any]:
    required = [str(term) for term in case.get("required_terms") or []]
    forbidden = [str(term) for term in case.get("forbidden_terms") or []]
    required_hits = [term for term in required if term.lower() in text.lower()]
    forbidden_hits = [term for term in forbidden if term.lower() in text.lower()]
    required_score = len(required_hits) / max(1, len(required))
    forbidden_score = 1.0 if not forbidden_hits else 0.0
    has_context = bool(str(case.get("inputs", {}).get("recent_context") or "").strip() and "Recent related context" in text)
    has_metrics = "Metrics JSON" in text
    structure_score = (int(has_context) + int(has_metrics)) / 2
    score = round((required_score * 0.7) + (forbidden_score * 0.15) + (structure_score * 0.15), 4)
    return {
        "quality": score,
        "required_hits": required_hits,
        "required_misses": [term for term in required if term not in required_hits],
        "forbidden_hits": forbidden_hits,
        "structure": {"has_recent_context_label": has_context, "has_metrics_json": has_metrics},
    }


def load_cases(path: Path = DEFAULT_CASES) -> list[dict[str, Any]]:
    data = load_json(path)
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list):
        raise ValueError(f"prompt efficiency cases missing list: {path}")
    return [case for case in cases if isinstance(case, dict)]


def evaluate_variant(variant: Variant, cases: list[dict[str, Any]], baseline_tokens: dict[str, int]) -> dict[str, Any]:
    case_results = []
    qualities = []
    token_counts = []
    for idx, case in enumerate(cases):
        if case.get("prompt_id") != variant.prompt_id:
            continue
        text = variant.renderer(case.get("inputs") or {})
        tokens = token_count(text)
        quality = quality_score(text, case)
        qualities.append(float(quality["quality"]))
        token_counts.append(tokens)
        case_results.append(
            {
                "case_id": case.get("id") or f"case-{idx + 1}",
                "quality": quality["quality"],
                "tokens": tokens,
                "compression_ratio": round(tokens / max(1, baseline_tokens.get(str(case.get("id") or idx), tokens)), 4),
                "required_misses": quality["required_misses"],
                "forbidden_hits": quality["forbidden_hits"],
            }
        )
    avg_quality = round(sum(qualities) / max(1, len(qualities)), 4)
    avg_tokens = round(sum(token_counts) / max(1, len(token_counts)), 2)
    return {
        "prompt_id": variant.prompt_id,
        "variant_id": variant.variant_id,
        "description": variant.description,
        "quality": avg_quality,
        "avg_tokens": avg_tokens,
        "cases": case_results,
    }


def evaluate_prompt(prompt_id: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = variant_for(prompt_id, "baseline")
    baseline_tokens: dict[str, int] = {}
    for idx, case in enumerate(cases):
        if case.get("prompt_id") != prompt_id:
            continue
        case_key = str(case.get("id") or idx)
        baseline_tokens[case_key] = token_count(baseline.renderer(case.get("inputs") or {}))
    results = [evaluate_variant(variant, cases, baseline_tokens) for variant in VARIANTS[prompt_id]]
    baseline_result = next(row for row in results if row["variant_id"] == "baseline")
    candidates = [
        row
        for row in results
        if row["variant_id"] != "baseline"
        and row["quality"] >= baseline_result["quality"]
        and row["avg_tokens"] < baseline_result["avg_tokens"]
    ]
    winner = min(candidates, key=lambda row: (row["avg_tokens"], -row["quality"])) if candidates else baseline_result
    adopted = winner["variant_id"] != "baseline"
    return {
        "prompt_id": prompt_id,
        "baseline": baseline_result,
        "variants": results,
        "winner": winner,
        "adopted": adopted,
        "quality_gate": "winner_quality >= baseline_quality",
        "compression_gate": "winner_avg_tokens < baseline_avg_tokens",
    }


def write_outputs(
    evaluations: list[dict[str, Any]],
    *,
    adoptions_path: Path = DEFAULT_ADOPTIONS,
    report_json: Path = DEFAULT_REPORT_JSON,
    report_md: Path = DEFAULT_REPORT_MD,
    state_md: Path = DEFAULT_STATE_MD,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    generated_at = utc_stamp(now)
    adoptions = {}
    for evaluation in evaluations:
        winner = evaluation["winner"]
        if evaluation["adopted"]:
            adoptions[evaluation["prompt_id"]] = {
                "variant_id": winner["variant_id"],
                "adopted_at": generated_at,
                "baseline_quality": evaluation["baseline"]["quality"],
                "winner_quality": winner["quality"],
                "baseline_avg_tokens": evaluation["baseline"]["avg_tokens"],
                "winner_avg_tokens": winner["avg_tokens"],
            }
    payload = {
        "schema": "prompt-efficiency-run.v1",
        "generated_at": generated_at,
        "evaluations": evaluations,
        "adoptions": adoptions,
    }
    for path, content in (
        (report_json, json.dumps(payload, indent=2, sort_keys=True) + "\n"),
        (adoptions_path, json.dumps({"schema": "prompt-efficiency-adoptions.v1", "updated_at": generated_at, "adoptions": adoptions}, indent=2, sort_keys=True) + "\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    markdown = render_markdown(payload)
    for path in (report_md, state_md):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Prompt Efficiency",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "| Prompt | Winner | Adopted | Quality | Avg tokens | Compression |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for evaluation in payload["evaluations"]:
        baseline = evaluation["baseline"]
        winner = evaluation["winner"]
        compression = round(1 - (float(winner["avg_tokens"]) / max(1.0, float(baseline["avg_tokens"]))), 4)
        lines.append(
            f"| {evaluation['prompt_id']} | {winner['variant_id']} | {str(evaluation['adopted']).lower()} | "
            f"{winner['quality']} / baseline {baseline['quality']} | {winner['avg_tokens']} / baseline {baseline['avg_tokens']} | {compression:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Guard",
            "",
            "A compressed variant is adopted only when quality is greater than or equal to baseline and token count is lower than baseline.",
            "Failed variants remain in the report as proof that the gate rejected under-specified compression.",
            "",
        ]
    )
    return "\n".join(lines)


def run(
    *,
    cases_path: Path = DEFAULT_CASES,
    adoptions_path: Path = DEFAULT_ADOPTIONS,
    report_json: Path = DEFAULT_REPORT_JSON,
    report_md: Path = DEFAULT_REPORT_MD,
    state_md: Path = DEFAULT_STATE_MD,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    cases = load_cases(cases_path)
    prompt_ids = sorted({str(case["prompt_id"]) for case in cases if case.get("prompt_id") in VARIANTS})
    evaluations = [evaluate_prompt(prompt_id, cases) for prompt_id in prompt_ids]
    return write_outputs(evaluations, adoptions_path=adoptions_path, report_json=report_json, report_md=report_md, state_md=state_md, now=now)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--adoptions", type=Path, default=DEFAULT_ADOPTIONS)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--state-md", type=Path, default=DEFAULT_STATE_MD)
    args = parser.parse_args(argv)
    payload = run(
        cases_path=args.cases,
        adoptions_path=args.adoptions,
        report_json=args.report_json,
        report_md=args.report_md,
        state_md=args.state_md,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
