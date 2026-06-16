#!/usr/bin/env python3
"""External benchmark intake plus inward agent score ledger.

The default path is offline and advisory. Live research collection must be
provided as a fixture or explicit provider command; this module normalizes those
findings, scores repo-local agent evidence, and writes a time-series ledger that
can recommend model/agent placement without changing production routing.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "agent-benchmark-intelligence.v1"
LEDGER_SCHEMA = "agent-scoring-ledger.v1"
DEFAULT_REPORT = REPO_ROOT / "core" / "BUILD" / "signals" / "agent_benchmark_intelligence.json"
DEFAULT_LEDGER = REPO_ROOT / "core" / "BUILD" / "signals" / "agent_scoring_ledger.jsonl"
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
DEFAULT_RESULTS_DIR = REPO_ROOT / "core" / "BUILD" / "results"
DEFAULT_REVIEWS_DIR = REPO_ROOT / "core" / "BUILD" / "reviews"
MAX_PROVIDER_COST_USD = 0.75
LIVE_TIMEOUT_SECONDS = 8

DIMENSIONS = ("code_quality", "critique_depth", "learning_speed", "reasoning")

DIMENSION_TERMS = {
    "code_quality": ("swe-bench", "swebench", "code", "coding", "unit test", "repository", "github"),
    "critique_depth": ("review", "critique", "judge", "rubric", "veto", "eval"),
    "learning_speed": ("learning", "adapt", "few-shot", "online", "improvement", "trajectory"),
    "reasoning": ("reasoning", "math", "mmlu", "gpqa", "livebench", "planning", "agentbench"),
}

SEED_FINDINGS: tuple[dict[str, Any], ...] = (
    {
        "source": "seed:SWE-bench style repo repair",
        "url": "https://www.swebench.com/",
        "summary": "Repository-grounded coding benchmarks emphasize real issue resolution, tests, and patch quality.",
        "dimensions": {"code_quality": 0.9, "reasoning": 0.55},
        "recommended_use": "Weight internal builder placement toward tests passed, rollback clarity, and small patch blast radius.",
    },
    {
        "source": "seed:AgentBench style task suites",
        "url": "https://github.com/THUDM/AgentBench",
        "summary": "Agent eval frameworks score multi-step tool use, planning, and evidence-grounded completion.",
        "dimensions": {"reasoning": 0.78, "critique_depth": 0.52},
        "recommended_use": "Prefer agents that leave evidence, guardrails, and next-step proof in result files.",
    },
    {
        "source": "seed:LiveBench / contamination-resistant evals",
        "url": "https://livebench.ai/",
        "summary": "Fresh evals reduce stale leaderboard confidence and reward recency-aware measurement.",
        "dimensions": {"reasoning": 0.72, "learning_speed": 0.6},
        "recommended_use": "Keep the scoring ledger time-series based and decay old placement confidence.",
    },
    {
        "source": "seed:LLM-as-judge rubric practice",
        "url": "repo-local",
        "summary": "Reviewer quality depends on explicit rubrics, concrete evidence, and finding fixes before approval.",
        "dimensions": {"critique_depth": 0.86, "code_quality": 0.36},
        "recommended_use": "Score independent reviewers by actionable findings and fixed blockers, not approval volume alone.",
    },
)

PUBLIC_BENCHMARK_SOURCES: tuple[dict[str, str], ...] = (
    {
        "name": "SWE-bench",
        "url": "https://www.swebench.com/",
        "summary": "Repository issue repair benchmark for coding-agent quality.",
    },
    {
        "name": "LiveBench",
        "url": "https://livebench.ai/",
        "summary": "Fresh contamination-resistant benchmark for reasoning and model capability drift.",
    },
    {
        "name": "AgentBench",
        "url": "https://github.com/THUDM/AgentBench",
        "summary": "Agent task-suite framework for planning, tool use, and multi-step evaluation.",
    },
    {
        "name": "HELM",
        "url": "https://crfm.stanford.edu/helm/",
        "summary": "Holistic evaluation framework with scenario and metric coverage.",
    },
)


@dataclasses.dataclass(frozen=True)
class ExternalFinding:
    finding_id: str
    source: str
    url: str
    summary: str
    dimensions: dict[str, float]
    recommended_use: str
    evidence: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class AgentEvidence:
    agent_id: str
    source: str
    source_kind: str
    metrics: dict[str, float]
    notes: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_external_findings(
    fixture_path: Path | None = None,
    *,
    provider_cmd: str | None = None,
    live_public_sources: bool = False,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[ExternalFinding]:
    """Load externally collected benchmark findings.

    The provider command is explicit and bounded by cost metadata. It is not a
    web crawler; it must return JSON so the scan can be reviewed and replayed.
    """
    payload: Any
    if fixture_path:
        payload = _load_json_or_jsonl(fixture_path)
    elif provider_cmd:
        payload = _run_provider(provider_cmd)
    elif live_public_sources:
        findings, warnings = collect_live_public_findings(opener=opener)
        if findings:
            return findings
        payload = [
            {
                **item,
                "evidence": [*item.get("evidence", []), *warnings],
            }
            for item in SEED_FINDINGS
        ]
    else:
        payload = list(SEED_FINDINGS)
    if isinstance(payload, dict):
        cost = float(payload.get("cost_usd") or 0.0)
        if cost > MAX_PROVIDER_COST_USD:
            raise ValueError(f"provider cost_usd {cost} exceeds cap {MAX_PROVIDER_COST_USD}")
        payload = payload.get("findings") or payload.get("candidates") or []
    if not isinstance(payload, list):
        raise ValueError("external findings payload must be a list or object with findings")
    return [normalize_finding(item) for item in payload if isinstance(item, dict)]


def collect_live_public_findings(
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> tuple[list[ExternalFinding], list[str]]:
    """Fetch a fixed public benchmark source list and normalize observations.

    This is intentionally narrow: no search queries, no credentialed APIs, no
    writes beyond the caller's report/ledger output, and no source text treated
    as instructions.
    """
    findings: list[ExternalFinding] = []
    warnings: list[str] = []
    for source in PUBLIC_BENCHMARK_SOURCES:
        url = source["url"]
        try:
            text = fetch_public_source(url, opener=opener)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            warnings.append(f"live fetch failed for {source['name']}: {exc}")
            continue
        snippet = clean(re.sub(r"<[^>]+>", " ", text))[:700]
        findings.append(
            normalize_finding(
                {
                    "source": f"live:{source['name']}",
                    "url": url,
                    "summary": f"{source['summary']} Current page signal: {snippet}",
                    "recommended_use": "Treat fetched benchmark page text as data for dimension weighting only.",
                    "evidence": [url, f"fetched_bytes={len(text.encode('utf-8', errors='ignore'))}"],
                }
            )
        )
    if warnings and findings:
        findings.append(
            normalize_finding(
                {
                    "source": "live:scan-warnings",
                    "url": "repo-local",
                    "summary": "Some fixed public benchmark sources failed during this scan.",
                    "dimensions": {dimension: 0.0 for dimension in DIMENSIONS},
                    "recommended_use": "Review scan completeness before treating the latest dimension weights as representative.",
                    "evidence": warnings,
                }
            )
        )
    return findings, warnings


def fetch_public_source(url: str, *, opener: Callable[..., Any] = urllib.request.urlopen) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "fpai-agent-benchmark-intelligence/0.1",
            "Accept": "text/html,text/plain,application/json",
        },
    )
    with opener(request, timeout=LIVE_TIMEOUT_SECONDS) as response:
        raw = response.read(200_000)
    text = raw.decode("utf-8", errors="replace")
    if len(clean(text)) < 40:
        raise ValueError("source returned too little text")
    return text


def normalize_finding(item: dict[str, Any]) -> ExternalFinding:
    source = clean(str(item.get("source") or item.get("name") or "unnamed benchmark finding"))
    url = clean(str(item.get("url") or ""))
    summary = clean(str(item.get("summary") or item.get("description") or ""))
    recommended_use = clean(str(item.get("recommended_use") or item.get("use") or "Review before changing placement."))
    raw_dimensions = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
    dimensions = infer_dimensions(" ".join([source, summary, recommended_use]), raw_dimensions)
    evidence = tuple(clean(str(value)) for value in item.get("evidence", []) if clean(str(value)))
    finding_id = stable_id("finding", source, url, summary)
    return ExternalFinding(
        finding_id=finding_id,
        source=source,
        url=url,
        summary=summary,
        dimensions=dimensions,
        recommended_use=recommended_use,
        evidence=evidence,
    )


def infer_dimensions(text: str, raw: dict[str, Any] | None = None) -> dict[str, float]:
    scores = {dimension: 0.0 for dimension in DIMENSIONS}
    for dimension, value in (raw or {}).items():
        if dimension in scores:
            scores[dimension] = clamp01(value)
    lowered = text.lower()
    for dimension, terms in DIMENSION_TERMS.items():
        hits = sum(1 for term in terms if term in lowered)
        if hits:
            scores[dimension] = max(scores[dimension], min(1.0, 0.28 + (hits * 0.18)))
    return {key: round(value, 4) for key, value in scores.items()}


def collect_internal_evidence(
    registry_path: Path = DEFAULT_REGISTRY,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    reviews_dir: Path = DEFAULT_REVIEWS_DIR,
) -> list[AgentEvidence]:
    evidence: list[AgentEvidence] = []
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for entry in registry.get("active_builds", []):
            if not isinstance(entry, dict):
                continue
            ev = evidence_from_registry_entry(entry, results_dir)
            if ev:
                evidence.append(ev)
    if reviews_dir.exists():
        for path in sorted(reviews_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            evidence.append(evidence_from_review(path, text))
    return evidence


def evidence_from_registry_entry(entry: dict[str, Any], results_dir: Path) -> AgentEvidence | None:
    build_id = clean(str(entry.get("id") or entry.get("slug") or ""))
    if not build_id:
        return None
    status = str(entry.get("status") or "").lower()
    if status not in {"done", "merged"}:
        return None
    agent_id = "codex-builder"
    result_path = results_dir / f"{build_id}.result.md"
    result_text = result_path.read_text(encoding="utf-8", errors="replace") if result_path.exists() else ""
    notes = clean(str(entry.get("notes") or ""))
    text = "\n".join([notes, result_text])
    tests_passed = 1.0 if entry.get("tests_passed") is True or re.search(r"tests?.*(ok|passed)", text, re.I) else 0.0
    rollback = 1.0 if re.search(r"\brollback\b", text, re.I) else 0.0
    risks = 1.0 if re.search(r"\brisks?\b", text, re.I) else 0.0
    intent = 1.0 if re.search(r"intent solved|downstream intent unlocked|next unlocked", text, re.I) else 0.0
    review_fix = 1.0 if re.search(r"request_changes|blockers? .*fixed|findings? .*fixed|veto", text, re.I) else 0.0
    independent = 1.0 if re.search(r"independent review|claude .*review|reviewer", text, re.I) else 0.0
    metrics = {
        "code_quality": weighted((tests_passed, 0.55), (rollback, 0.18), (risks, 0.17), (independent, 0.10)),
        "critique_depth": weighted((independent, 0.45), (review_fix, 0.35), (risks, 0.20)),
        "learning_speed": weighted((review_fix, 0.45), (intent, 0.25), (tests_passed, 0.30)),
        "reasoning": weighted((intent, 0.38), (risks, 0.22), (rollback, 0.18), (independent, 0.22)),
    }
    return AgentEvidence(
        agent_id=agent_id,
        source=build_id,
        source_kind="build_result",
        metrics=metrics,
        notes=tuple(note for note in (status, "tests_passed" if tests_passed else "tests_missing", "result_file" if result_path.exists() else "no_result_file") if note),
    )


def evidence_from_review(path: Path, text: str) -> AgentEvidence:
    lowered = text.lower()
    findings = len(re.findall(r"\b(finding|blocker|risk|request_changes|request changes)\b", lowered))
    evidence_refs = len(re.findall(r"`[^`]+`|:[0-9]+|\bline\b|\bfile\b", text))
    approval = 1.0 if re.search(r"\b(approve|approved|no blockers?|no issues?)\b", lowered) else 0.0
    actionable = min(1.0, findings / 4.0)
    grounded = min(1.0, evidence_refs / 8.0)
    metrics = {
        "code_quality": weighted((approval, 0.35), (grounded, 0.30), (actionable, 0.35)),
        "critique_depth": weighted((actionable, 0.50), (grounded, 0.38), (approval, 0.12)),
        "learning_speed": weighted((actionable, 0.45), (grounded, 0.25), (approval, 0.30)),
        "reasoning": weighted((grounded, 0.42), (actionable, 0.38), (approval, 0.20)),
    }
    return AgentEvidence(
        agent_id="independent-reviewer",
        source=str(path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path),
        source_kind="review_markdown",
        metrics=metrics,
        notes=(f"findings={findings}", f"evidence_refs={evidence_refs}"),
    )


def aggregate_agent_scores(
    evidence: Iterable[AgentEvidence],
    findings: Iterable[ExternalFinding],
) -> list[dict[str, Any]]:
    dimension_weights = benchmark_dimension_weights(findings)
    grouped: dict[str, list[AgentEvidence]] = {}
    for row in evidence:
        grouped.setdefault(row.agent_id, []).append(row)
    agents: list[dict[str, Any]] = []
    for agent_id, rows in sorted(grouped.items()):
        dimensions = {
            dimension: round(avg(row.metrics.get(dimension, 0.0) for row in rows), 4)
            for dimension in DIMENSIONS
        }
        overall = round(sum(dimensions[d] * dimension_weights[d] for d in DIMENSIONS), 4)
        agents.append(
            {
                "agent_id": agent_id,
                "evidence_count": len(rows),
                "dimensions": dimensions,
                "weighted_score": overall,
                "placement": recommend_placement(agent_id, dimensions, overall),
                "recent_sources": [row.source for row in rows[-5:]],
            }
        )
    return sorted(agents, key=lambda item: (-item["weighted_score"], item["agent_id"]))


def benchmark_dimension_weights(findings: Iterable[ExternalFinding]) -> dict[str, float]:
    totals = {dimension: 1.0 for dimension in DIMENSIONS}
    for finding in findings:
        for dimension in DIMENSIONS:
            totals[dimension] += finding.dimensions.get(dimension, 0.0)
    total = sum(totals.values()) or 1.0
    return {dimension: round(totals[dimension] / total, 4) for dimension in DIMENSIONS}


def recommend_placement(agent_id: str, dimensions: dict[str, float], overall: float) -> dict[str, Any]:
    strongest = max(DIMENSIONS, key=lambda dimension: dimensions.get(dimension, 0.0))
    weakest = min(DIMENSIONS, key=lambda dimension: dimensions.get(dimension, 0.0))
    if overall >= 0.78 and dimensions.get("code_quality", 0) >= 0.72:
        role = "primary_builder"
    elif dimensions.get("critique_depth", 0) >= 0.68:
        role = "independent_reviewer"
    elif dimensions.get("reasoning", 0) >= 0.68:
        role = "planner_or_router"
    elif overall >= 0.55:
        role = "specialist_with_review"
    else:
        role = "shadow_only"
    return {
        "role": role,
        "authority": "advisory-only",
        "strongest_dimension": strongest,
        "weakest_dimension": weakest,
        "gate": "Placement recommendations cannot change routing, spend, training, deployment, or outreach without James/Ember review.",
        "agent": agent_id,
    }


def build_report(
    *,
    external_findings: list[ExternalFinding],
    internal_evidence: list[AgentEvidence],
    now: str | None = None,
) -> dict[str, Any]:
    weights = benchmark_dimension_weights(external_findings)
    agents = aggregate_agent_scores(internal_evidence, external_findings)
    return {
        "schema": SCHEMA,
        "generated_at": now or utc_now(),
        "guardrails": [
            "advisory-only",
            "no default network access",
            "no model downloads",
            "no training",
            "no production routing",
            "no spend without explicit provider fixture/command and cost cap",
        ],
        "lantern": {
            "external_findings": [finding.to_json() for finding in external_findings],
            "dimension_weights": weights,
        },
        "mirror": {
            "internal_evidence_count": len(internal_evidence),
            "agents": agents,
        },
        "ledger": {
            "schema": LEDGER_SCHEMA,
            "recommended_path": str(DEFAULT_LEDGER.relative_to(REPO_ROOT)),
            "append_mode": "one row per agent per run",
        },
    }


def ledger_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agent in report.get("mirror", {}).get("agents", []):
        rows.append(
            {
                "schema": LEDGER_SCHEMA,
                "at": report.get("generated_at"),
                "agent_id": agent["agent_id"],
                "dimensions": agent["dimensions"],
                "weighted_score": agent["weighted_score"],
                "placement": agent["placement"],
                "evidence_count": agent["evidence_count"],
                "external_weight_signature": stable_id(
                    "weights",
                    json.dumps(report.get("lantern", {}).get("dimension_weights", {}), sort_keys=True),
                ),
            }
        )
    return rows


def append_ledger(rows: Iterable[dict[str, Any]], path: Path = DEFAULT_LEDGER) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def write_json(data: dict[str, Any], path: Path = DEFAULT_REPORT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_json_or_jsonl(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def _run_provider(command: str) -> Any:
    argv = shlex.split(command)
    if not argv:
        raise ValueError("provider command is empty")
    completed = subprocess.run(
        argv,
        input=json.dumps({"task": "agent_benchmark_findings", "schema": SCHEMA}),
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"provider exited {completed.returncode}")
    return json.loads(completed.stdout)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def clamp01(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, number)), 4)


def weighted(*items: tuple[float, float]) -> float:
    return round(sum(clamp01(value) * weight for value, weight in items), 4)


def avg(values: Iterable[float]) -> float:
    rows = list(values)
    return sum(rows) / len(rows) if rows else 0.0


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:16]}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the advisory agent benchmarking intelligence report.")
    parser.add_argument("--external-findings", type=Path, default=None, help="JSON/JSONL external benchmark findings fixture")
    parser.add_argument("--provider-cmd", default=os.environ.get("AGENT_BENCHMARK_PROVIDER_CMD"), help="explicit JSON provider command")
    parser.add_argument("--live-public-sources", action="store_true", help="fetch fixed public benchmark source URLs")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--reviews-dir", type=Path, default=DEFAULT_REVIEWS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--append-ledger", action="store_true", help="append one JSONL ledger row per scored agent")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args(argv)

    findings = load_external_findings(
        args.external_findings,
        provider_cmd=args.provider_cmd,
        live_public_sources=args.live_public_sources,
    )
    evidence = collect_internal_evidence(args.registry, args.results_dir, args.reviews_dir)
    report = build_report(external_findings=findings, internal_evidence=evidence)
    write_json(report, args.output)
    if args.append_ledger:
        append_ledger(ledger_rows(report), args.ledger)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
