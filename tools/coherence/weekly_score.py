#!/usr/bin/env python3
"""Score whether the repo-facing FPOS surfaces speak with one voice.

This is a deterministic weekly optimizer pass. It reads bounded repo evidence,
scores alignment to the canonical voice, and writes a report with concrete gaps
instead of asking James to reconcile stale surfaces by hand.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
DEFAULT_JSON = REPO_ROOT / "core" / "BUILD" / "signals" / "coherence_score.json"
DEFAULT_MD = REPO_ROOT / "core" / "BUILD" / "signals" / "coherence_score.md"
DEFAULT_STATE = REPO_ROOT / "core" / "STATE" / "COHERENCE_SCORE.md"
SCHEMA = "coherence-weekly-score.v1"

SOURCE_PATHS = (
    "docs/codex/AI_PROTOCOLS.md",
    "docs/codex/INTENT_BUILDSTREAM.md",
    "docs/codex/HANDOFF.md",
    "docs/codex/ATTENTION_FLOW.md",
    "core/STATE/NORTH_STAR.md",
    "core/STATE/SELF_PORTRAIT.md",
    "core/STATE/HOT_STATE.md",
    "core/STATE/MODEL_DNA.md",
)

VOICE_SIGNALS: dict[str, tuple[str, ...]] = {
    "source": ("coherence", "north star", "full potential os", "fpos"),
    "routing": ("route", "routing", "downstream", "upstream", "buildstream"),
    "proof": ("proof", "tested", "evidence", "verified", "result"),
    "memory": ("memory", "remember", "context", "self-portrait", "hot_state"),
    "safety": ("reserved class", "resource discipline gate", "secrets", "deploy", "money"),
    "next_intent": ("unlocks next", "downstream intent", "next move", "adjacent intent"),
}

DRIFT_PATTERNS: dict[str, re.Pattern[str]] = {
    "stale_surface": re.compile(r"\bstale\b|\bout of sync\b|\bdrift\b", re.I),
    "missing_proof": re.compile(r"\bproof\s*:\s*(none|unknown|tbd|-)\b", re.I),
    "unclear_next": re.compile(r"\bnext\s*(move|action)\s*:\s*(none|unknown|tbd|-)\b", re.I),
    "main_branch_risk": re.compile(r"\bbranch\b[^\n]{0,80}\bmain\b", re.I),
}
NEGATED_DRIFT_HINTS = (
    "never main",
    "never push",
    "do not push",
    "not main",
    "no stale",
    "without stale",
    "must not rely on stale",
    "stale-prone",
    "fixed",
)


@dataclass(frozen=True)
class SourceScore:
    path: str
    exists: bool
    age_days: float | None
    signals: tuple[str, ...]
    drift_flags: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "age_days": self.age_days,
            "signals": list(self.signals),
            "drift_flags": list(self.drift_flags),
        }


@dataclass(frozen=True)
class CoherenceReport:
    score: float
    status: str
    generated_at: str
    components: dict[str, float]
    sources: tuple[SourceScore, ...]
    registry_gaps: tuple[str, ...]
    recommendations: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "generated_at": self.generated_at,
            "score": self.score,
            "status": self.status,
            "components": self.components,
            "sources": [source.to_json() for source in self.sources],
            "registry_gaps": list(self.registry_gaps),
            "recommendations": list(self.recommendations),
        }


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(value: dt.datetime | None = None) -> str:
    return (value or utc_now()).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _age_days(path: Path, now: dt.datetime) -> float | None:
    try:
        modified = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
    except OSError:
        return None
    return max(0.0, round((now - modified).total_seconds() / 86400, 2))


def _signals(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    found = []
    for signal, needles in VOICE_SIGNALS.items():
        if any(needle in lowered for needle in needles):
            found.append(signal)
    return tuple(found)


def _current_text_for_path(rel_path: str, text: str) -> str:
    if rel_path == "docs/codex/HANDOFF.md":
        return text.split("## 📥 CODEX", 1)[0]
    return text


def _drift_flags(text: str, *, rel_path: str) -> tuple[str, ...]:
    if rel_path in {
        "docs/codex/AI_PROTOCOLS.md",
        "docs/codex/INTENT_BUILDSTREAM.md",
        "docs/codex/ATTENTION_FLOW.md",
    }:
        active_patterns = {key: value for key, value in DRIFT_PATTERNS.items() if key != "stale_surface"}
    else:
        active_patterns = DRIFT_PATTERNS
    scoped_text = _current_text_for_path(rel_path, text)
    flags: set[str] = set()
    for raw in scoped_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower()
        for flag, pattern in active_patterns.items():
            if not pattern.search(line):
                continue
            if any(hint in lowered for hint in NEGATED_DRIFT_HINTS):
                continue
            if flag == "main_branch_risk" and ("do not" in lowered or "never" in lowered or "not main" in lowered):
                continue
            flags.add(flag)
    return tuple(sorted(flags))


def score_sources(repo_root: Path, *, now: dt.datetime, sources: tuple[str, ...] = SOURCE_PATHS) -> tuple[SourceScore, ...]:
    results: list[SourceScore] = []
    for rel in sources:
        path = repo_root / rel
        text = _read_text(path)
        results.append(
            SourceScore(
                path=rel,
                exists=path.exists(),
                age_days=_age_days(path, now),
                signals=_signals(text),
                drift_flags=_drift_flags(text, rel_path=rel),
            )
        )
    return tuple(results)


def registry_gaps(path: Path) -> tuple[str, ...]:
    data = _read_json(path)
    builds = data.get("active_builds") or []
    if not isinstance(builds, list):
        return ("registry active_builds is not a list",)
    gaps: list[str] = []
    building_slugs: dict[str, int] = {}
    for build in builds:
        if not isinstance(build, dict):
            continue
        slug = str(build.get("slug") or build.get("id") or "unknown")
        status = str(build.get("status") or "")
        branch = str(build.get("branch") or "")
        tests_passed = build.get("tests_passed")
        if status == "building":
            building_slugs[slug] = building_slugs.get(slug, 0) + 1
        if status == "done" and tests_passed is not True:
            gaps.append(f"{slug}: status done but tests_passed is not true")
        if branch == "main" or branch.endswith("/main"):
            gaps.append(f"{slug}: branch points at main")
        if build.get("base_branch") and build.get("base_branch") != "feat/headless-build":
            gaps.append(f"{slug}: base_branch is {build.get('base_branch')}, expected feat/headless-build")
    for slug, count in building_slugs.items():
        if count > 1:
            gaps.append(f"{slug}: duplicate building entries ({count})")
    return tuple(gaps)


def _component_scores(sources: tuple[SourceScore, ...], gaps: tuple[str, ...], *, freshness_days: float) -> dict[str, float]:
    existing = [source for source in sources if source.exists]
    source_coverage = len(existing) / len(sources) if sources else 0.0
    all_signals = set().union(*(set(source.signals) for source in existing)) if existing else set()
    signal_coverage = len(all_signals) / len(VOICE_SIGNALS) if VOICE_SIGNALS else 0.0
    fresh = [source for source in existing if source.age_days is not None and source.age_days <= freshness_days]
    freshness = len(fresh) / len(existing) if existing else 0.0
    drift_count = sum(len(source.drift_flags) for source in existing)
    drift_penalty = max(0.0, 1.0 - min(1.0, drift_count / 8.0))
    registry = max(0.0, 1.0 - min(1.0, len(gaps) / 5.0))
    return {
        "source_coverage": round(source_coverage, 4),
        "voice_signal_coverage": round(signal_coverage, 4),
        "freshness": round(freshness, 4),
        "drift_penalty": round(drift_penalty, 4),
        "registry_hygiene": round(registry, 4),
    }


def _recommendations(sources: tuple[SourceScore, ...], gaps: tuple[str, ...]) -> tuple[str, ...]:
    recs: list[str] = []
    missing = [source.path for source in sources if not source.exists]
    if missing:
        recs.append("Create or refresh missing coherence surfaces: " + ", ".join(missing[:4]))
    weak = [source.path for source in sources if source.exists and len(source.signals) < 2]
    if weak:
        recs.append("Reconcile low-signal surfaces with AI_PROTOCOLS/INTENT_BUILDSTREAM: " + ", ".join(weak[:4]))
    drift = [f"{source.path} ({', '.join(source.drift_flags)})" for source in sources if source.drift_flags]
    if drift:
        recs.append("Review drift flags before the next autonomous run: " + "; ".join(drift[:4]))
    if gaps:
        recs.append("Fix registry hygiene gaps: " + "; ".join(gaps[:3]))
    if not recs:
        recs.append("No immediate coherence repair found; keep weekly score running and compare the trend.")
    return tuple(recs)


def build_report(
    *,
    repo_root: Path = REPO_ROOT,
    registry_path: Path = DEFAULT_REGISTRY,
    now: dt.datetime | None = None,
    freshness_days: float = 14.0,
) -> CoherenceReport:
    current = now or utc_now()
    sources = score_sources(repo_root, now=current)
    gaps = registry_gaps(registry_path)
    components = _component_scores(sources, gaps, freshness_days=freshness_days)
    score = round(
        (
            components["source_coverage"] * 0.25
            + components["voice_signal_coverage"] * 0.30
            + components["freshness"] * 0.20
            + components["drift_penalty"] * 0.15
            + components["registry_hygiene"] * 0.10
        )
        * 100,
        1,
    )
    status = "PASS" if score >= 80 else "WATCH" if score >= 65 else "REPAIR"
    return CoherenceReport(
        score=score,
        status=status,
        generated_at=utc_stamp(current),
        components=components,
        sources=sources,
        registry_gaps=gaps,
        recommendations=_recommendations(sources, gaps),
    )


def render_markdown(report: CoherenceReport) -> str:
    lines = [
        "# Coherence Score",
        "",
        "classification: COUNCIL-OPEN",
        "privacy: repo-surface synthesis only; no secrets, private messages, or external scans",
        "generated_by: d103 coherence weekly score",
        f"generated_at: {report.generated_at}",
        f"status: {report.status}",
        f"score: {report.score}/100",
        "",
        "## Components",
        "",
    ]
    for key, value in report.components.items():
        lines.append(f"- {key}: {value:.1%}")
    lines.extend(["", "## Source Signals", ""])
    for source in report.sources:
        age = "missing" if source.age_days is None else f"{source.age_days}d"
        signals = ", ".join(source.signals) if source.signals else "none"
        flags = ", ".join(source.drift_flags) if source.drift_flags else "none"
        lines.append(f"- {source.path}: exists={source.exists}; age={age}; signals={signals}; drift={flags}")
    lines.extend(["", "## Registry Gaps", ""])
    if report.registry_gaps:
        lines.extend(f"- {gap}" for gap in report.registry_gaps)
    else:
        lines.append("- none")
    lines.extend(["", "## Recommended Repairs", ""])
    lines.extend(f"- {item}" for item in report.recommendations)
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: CoherenceReport,
    *,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MD,
    state_path: Path = DEFAULT_STATE,
) -> None:
    payload = json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n"
    rendered = render_markdown(report)
    for path, content in ((json_path, payload), (markdown_path, rendered), (state_path, rendered)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-path", type=Path, default=DEFAULT_MD)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--freshness-days", type=float, default=14.0)
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    parser.add_argument("--no-write", action="store_true", help="Do not write report artifacts.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(repo_root=args.repo_root, registry_path=args.registry, freshness_days=args.freshness_days)
    if not args.no_write:
        write_report(report, json_path=args.json_path, markdown_path=args.markdown_path, state_path=args.state_path)
    if args.json:
        print(json.dumps(report.to_json(), sort_keys=True))
    else:
        print(f"coherence score: {report.score}/100 ({report.status})")
    return 0 if report.score >= 65 else 1


if __name__ == "__main__":
    raise SystemExit(main())
