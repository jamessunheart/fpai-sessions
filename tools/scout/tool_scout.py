#!/usr/bin/env python3
"""Tool Scout Agent.

Ranks GitHub/product/model/tool-drop candidates for early adoption. The agent is
research-input driven: live web/API collection must happen outside this module
or through an explicit provider command. This module validates, scores, reports,
and feeds review-gated signals back into the build loop.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable

from tools.platform_bias.registry import rate_tool

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = REPO_ROOT / "core" / "BUILD" / "signals" / "tool_scout_report.md"
DEFAULT_PROPOSALS = REPO_ROOT / "core" / "BUILD" / "signals" / "tool_scout_proposals.jsonl"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
MAX_COST_USD = 1.50
LIVE_TIMEOUT = 8
FORBIDDEN_ACTION_RE = re.compile(
    r"\b(install|deploy|send|purchase|subscribe|wire|wallet|secret|credential|production)\b",
    re.IGNORECASE,
)
GITHUB_SEARCHES = (
    ("agent framework llm tool", ("agents", "workflow")),
    ("model router llm budget provider", ("model", "router", "budget")),
    ("ai coding agent cli", ("codex", "agents")),
)
RELEASE_REPOS = (
    ("BerriAI/litellm", "model router and provider budget layer"),
    ("getzep/graphiti", "temporal memory graph"),
    ("microsoft/autogen", "multi-agent orchestration framework"),
)


class ToolScoutError(RuntimeError):
    """Provider or payload failed validation."""


@dataclasses.dataclass(frozen=True)
class ToolCandidate:
    name: str
    url: str
    source_kind: str
    summary: str
    proposed_use: str
    replaces: str
    leverage: int
    maturity: int
    integration_cost: int
    risk: int
    released_at: str = ""
    evidence: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    @property
    def score(self) -> int:
        freshness = freshness_bonus(self.released_at)
        replacement = 3 if self.replaces.strip() else 0
        return self.leverage + self.maturity + freshness + replacement - self.integration_cost - self.risk

    @property
    def verdict(self) -> str:
        if self.risk >= 7 or self.integration_cost >= 8:
            return "watch"
        if self.score >= 13:
            return "adopt-spec"
        if self.score >= 9:
            return "pilot-spec"
        return "watch"


SEED_CANDIDATES: tuple[ToolCandidate, ...] = (
    ToolCandidate(
        name="Claude Code Skills",
        url="https://docs.anthropic.com/",
        source_kind="ai-tool-drop",
        summary="Reusable task instructions packaged as skills for repeatable agent workflows.",
        proposed_use="Mirror stable FPOS operating workflows into small repo-local skills after they prove useful.",
        replaces="ad hoc repeated prompts",
        leverage=8,
        maturity=7,
        integration_cost=3,
        risk=3,
        tags=("skills", "agents", "workflow", "codex", "memory"),
    ),
    ToolCandidate(
        name="LiteLLM Proxy",
        url="https://github.com/BerriAI/litellm",
        source_kind="github",
        summary="Provider abstraction, fallback, budget, and observability layer for model calls.",
        proposed_use="Review as a future Resource Discipline Gate component for paid API calls.",
        replaces="hand-coded provider routing",
        leverage=9,
        maturity=8,
        integration_cost=5,
        risk=4,
        tags=("model", "router", "budget", "provider"),
    ),
    ToolCandidate(
        name="Graphiti",
        url="https://github.com/getzep/graphiti",
        source_kind="github",
        summary="Temporal knowledge graph pattern for AI memory over entities, events, and relationships.",
        proposed_use="Pilot against one non-sensitive repo-local stream before any memory migration.",
        replaces="flat episodic memory search for entity/time recall",
        leverage=8,
        maturity=6,
        integration_cost=7,
        risk=5,
        tags=("memory", "graph", "temporal"),
    ),
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def freshness_bonus(raw: str) -> int:
    if not raw:
        return 0
    try:
        released = dt.date.fromisoformat(raw[:10])
    except ValueError:
        return 0
    age = (today() - released).days
    if age <= 30:
        return 4
    if age <= 90:
        return 2
    if age <= 180:
        return 1
    return 0


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def load_provider_payload(prompt: str, *, fixture_path: Path | None = None, live: bool = False) -> dict[str, Any]:
    if fixture_path:
        return json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_env = os.environ.get("TOOL_SCOUT_FIXTURE_JSON")
    if fixture_env:
        return json.loads(Path(fixture_env).read_text(encoding="utf-8"))
    command = os.environ.get("TOOL_SCOUT_PROVIDER_CMD")
    if not command:
        if live:
            return collect_live_payload()
        return {"cost_usd": 0.0, "candidates": [dataclasses.asdict(candidate) for candidate in SEED_CANDIDATES]}
    result = subprocess.run(command, input=prompt, shell=True, text=True, capture_output=True, timeout=180, check=False)
    if result.returncode != 0:
        raise ToolScoutError(result.stderr.strip() or f"provider exited {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ToolScoutError("provider returned non-JSON output") from exc


def fetch_json(url: str, *, opener: Callable[..., Any] = urllib.request.urlopen) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json, application/json",
            "User-Agent": "fpai-tool-scout/0.1",
        },
    )
    with opener(request, timeout=LIVE_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def collect_live_payload(*, opener: Callable[..., Any] = urllib.request.urlopen) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    for query, tags in GITHUB_SEARCHES:
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
            {"q": query, "sort": "updated", "order": "desc", "per_page": "3"}
        )
        try:
            payload = fetch_json(url, opener=opener)
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(f"github search failed for {query}: {exc}")
            continue
        for item in payload.get("items", [])[:3]:
            candidate = github_repo_candidate(item, source_kind="github-search", tags=tags)
            if candidate:
                candidates.append(candidate)
    for repo, use in RELEASE_REPOS:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            payload = fetch_json(url, opener=opener)
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(f"github release failed for {repo}: {exc}")
            continue
        candidate = github_release_candidate(payload, repo=repo, proposed_use=use)
        if candidate:
            candidates.append(candidate)
    if not candidates:
        return {
            "cost_usd": 0.0,
            "provider_mode": "live-fallback-seeds",
            "warnings": warnings,
            "candidates": [dataclasses.asdict(candidate) for candidate in SEED_CANDIDATES],
        }
    return {
        "cost_usd": 0.0,
        "provider_mode": "live-github",
        "warnings": warnings,
        "candidates": dedupe_candidates(candidates),
    }


def github_repo_candidate(item: dict[str, Any], *, source_kind: str, tags: tuple[str, ...]) -> dict[str, Any] | None:
    name = clean(str(item.get("full_name") or item.get("name") or ""))
    url = clean(str(item.get("html_url") or ""))
    summary = clean(str(item.get("description") or "GitHub repository candidate"))
    if not name or not url:
        return None
    stars = int(item.get("stargazers_count") or 0)
    maturity = min(10, max(3, 5 + (2 if stars > 1000 else 0) + (1 if stars > 10000 else 0)))
    leverage = 8 if any(tag in {"model", "router", "agents"} for tag in tags) else 6
    return {
        "name": name,
        "url": url,
        "source_kind": source_kind,
        "summary": summary,
        "proposed_use": "Review as a candidate for a narrow adoption spec",
        "replaces": "",
        "leverage": leverage,
        "maturity": maturity,
        "integration_cost": 5,
        "risk": 4,
        "released_at": clean(str(item.get("pushed_at") or ""))[:10],
        "evidence": [f"stars={stars}", f"updated={clean(str(item.get('pushed_at') or 'unknown'))}"],
        "tags": tags,
    }


def github_release_candidate(payload: dict[str, Any], *, repo: str, proposed_use: str) -> dict[str, Any] | None:
    url = clean(str(payload.get("html_url") or ""))
    if not url:
        return None
    return {
        "name": repo,
        "url": url,
        "source_kind": "github-release",
        "summary": clean(str(payload.get("name") or payload.get("tag_name") or "Latest release")),
        "proposed_use": f"Review latest release for {proposed_use}",
        "replaces": "",
        "leverage": 8,
        "maturity": 7,
        "integration_cost": 5,
        "risk": 4,
        "released_at": clean(str(payload.get("published_at") or ""))[:10],
        "evidence": [f"repo={repo}", f"tag={clean(str(payload.get('tag_name') or 'unknown'))}"],
        "tags": ("github", "release", "agents"),
    }


def dedupe_candidates(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("url") or row.get("name") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def validate_payload(payload: dict[str, Any]) -> list[ToolCandidate]:
    cost = float(payload.get("cost_usd", 0.0) or 0.0)
    if cost > MAX_COST_USD:
        raise ToolScoutError(f"cost cap exceeded: ${cost:.2f} > ${MAX_COST_USD:.2f}")
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ToolScoutError("expected non-empty candidates list")
    candidates: list[ToolCandidate] = []
    for idx, row in enumerate(raw_candidates, start=1):
        if not isinstance(row, dict):
            raise ToolScoutError(f"candidate {idx} is not an object")
        name = clean(str(row.get("name") or ""))
        url = clean(str(row.get("url") or ""))
        summary = clean(str(row.get("summary") or ""))
        proposed_use = clean(str(row.get("proposed_use") or row.get("use") or ""))
        if not name or not url.startswith(("http://", "https://")) or not summary or not proposed_use:
            raise ToolScoutError(f"candidate {idx} needs name, http(s) url, summary, proposed_use")
        if FORBIDDEN_ACTION_RE.search(proposed_use):
            raise ToolScoutError(f"candidate {idx} proposed_use includes action outside scout authority")
        candidates.append(ToolCandidate(
            name=name,
            url=url,
            source_kind=clean(str(row.get("source_kind") or row.get("source") or "unknown")),
            summary=summary,
            proposed_use=proposed_use,
            replaces=clean(str(row.get("replaces") or "")),
            leverage=bounded_int(row.get("leverage"), "leverage", idx),
            maturity=bounded_int(row.get("maturity"), "maturity", idx),
            integration_cost=bounded_int(row.get("integration_cost"), "integration_cost", idx),
            risk=bounded_int(row.get("risk"), "risk", idx),
            released_at=clean(str(row.get("released_at") or "")),
            evidence=tuple(clean(str(item)) for item in row.get("evidence", []) if clean(str(item))),
            tags=tuple(clean(str(item)).lower() for item in row.get("tags", []) if clean(str(item))),
        ))
    return candidates


def bounded_int(value: Any, field: str, idx: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ToolScoutError(f"candidate {idx} field {field} must be 0-10") from exc
    if parsed < 0 or parsed > 10:
        raise ToolScoutError(f"candidate {idx} field {field} must be 0-10")
    return parsed


def focus_terms(focus: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", focus.lower()) if len(word) > 2}


def focus_bonus(candidate: ToolCandidate, terms: set[str]) -> int:
    return min(4, len(terms.intersection(candidate.tags)) * 2) if terms else 0


def ranked_score(candidate: ToolCandidate, focus: str) -> int:
    return candidate.score + focus_bonus(candidate, focus_terms(focus))


def verdict_for(candidate: ToolCandidate, focus: str) -> str:
    if candidate.risk >= 7 or candidate.integration_cost >= 8:
        return "watch"
    score = ranked_score(candidate, focus)
    if score >= 13:
        return "adopt-spec"
    if score >= 9:
        return "pilot-spec"
    return "watch"


def rank(candidates: Iterable[ToolCandidate], focus: str) -> list[ToolCandidate]:
    terms = {word for word in re.findall(r"[a-z0-9]+", focus.lower()) if len(word) > 2}

    def key(candidate: ToolCandidate) -> tuple[int, int, str]:
        return (candidate.score + focus_bonus(candidate, terms), -candidate.integration_cost, candidate.name)

    return sorted(candidates, key=key, reverse=True)


def proposal_for(candidate: ToolCandidate, *, focus: str) -> dict[str, object]:
    proposed_use = candidate.proposed_use.rstrip(".")
    rating = rate_tool(candidate.name, candidate.url, candidate.tags)
    return {
        "source": "tool_scout",
        "title": f"Scout adoption candidate: {candidate.name}",
        "spec": (
            f"Review {candidate.name} ({candidate.url}) as a review-gated adoption candidate. "
            f"Proposed use: {proposed_use}. Replacement target: {candidate.replaces or 'none declared'}. "
            f"Sovereignty rating: {rating.rating} ({rating.reason}). {rating.alternative_prompt} "
            "Do not install, spend, deploy, or wire credentials in the scout pass; produce a narrow adoption spec first."
        ),
        "route": "codex",
        "verdict": verdict_for(candidate, focus),
        "score": ranked_score(candidate, focus),
        "url": candidate.url,
        "sovereignty_rating": rating.rating,
        "sovereignty_reason": rating.reason,
        "safe_auto": False,
        "needs_review": True,
    }


def render_report(candidates: list[ToolCandidate], *, focus: str, generated_at: str, cost_usd: float) -> str:
    lines = [
        "# Tool Scout Report",
        "",
        f"**Generated:** {generated_at}",
        f"**Focus:** {focus}",
        f"**Research cost:** ${cost_usd:.2f} (cap ${MAX_COST_USD:.2f})",
        "**Mode:** review-gated ranking only; no installs, purchases, deploys, secrets, or automatic adoption.",
        "",
        "## Top Candidates",
        "",
        "| Score | Verdict | Candidate | Source | Sovereignty | Replaces |",
        "|---:|---|---|---|---|---|",
    ]
    for candidate in candidates:
        rating = rate_tool(candidate.name, candidate.url, candidate.tags)
        lines.append(
            f"| {ranked_score(candidate, focus)} | {verdict_for(candidate, focus)} | [{candidate.name}]({candidate.url}) | "
            f"{candidate.source_kind} | {rating.rating} | {candidate.replaces or '-'} |"
        )
    lines.extend(["", "## Notes", ""])
    for candidate in candidates:
        evidence = "; ".join(candidate.evidence) if candidate.evidence else "review source manually before adoption"
        rating = rate_tool(candidate.name, candidate.url, candidate.tags)
        lines.extend(
            [
                f"### {candidate.name}",
                f"- **Summary:** {candidate.summary}",
                f"- **Proposed use:** {candidate.proposed_use}",
                f"- **Sovereignty:** {rating.rating} — {rating.reason}. {rating.alternative_prompt}",
                f"- **Score inputs:** leverage {candidate.leverage}, maturity {candidate.maturity}, cost {candidate.integration_cost}, risk {candidate.risk}",
                f"- **Evidence:** {evidence}",
                "",
            ]
        )
    return "\n".join(lines)


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def append_ops(ledger: Path, *, candidate_count: int, report: Path, proposals: Path) -> bool:
    row = {
        "ts": utc_now(),
        "loop": "tool_scout",
        "event": "proposed" if candidate_count else "ran",
        "detail": f"tool scout ranked {candidate_count} candidates",
        "cost": "$0 marginal unless provider command reports metered cost",
        "artifact": str(report),
        "next": f"review {proposals}" if candidate_count else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def run(
    *,
    focus: str,
    fixture_path: Path | None = None,
    report_path: Path = DEFAULT_REPORT,
    proposals_path: Path = DEFAULT_PROPOSALS,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    no_ledger: bool = False,
    max_proposals: int = 5,
    live: bool = False,
) -> dict[str, object]:
    prompt = (
        "Return JSON with cost_usd and candidates for high-value GitHub, product release, "
        "AI tool, or model replacement discoveries. Candidate fields: name, url, source_kind, "
        "summary, proposed_use, replaces, leverage, maturity, integration_cost, risk, released_at, evidence, tags. "
        f"Focus: {focus}"
    )
    payload = load_provider_payload(prompt, fixture_path=fixture_path, live=live)
    cost_usd = float(payload.get("cost_usd", 0.0) or 0.0)
    candidates = rank(validate_payload(payload), focus)
    generated_at = utc_now()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(candidates, focus=focus, generated_at=generated_at, cost_usd=cost_usd), encoding="utf-8")
    proposals = [
        proposal_for(candidate, focus=focus)
        for candidate in candidates
        if verdict_for(candidate, focus) in {"adopt-spec", "pilot-spec"}
    ][:max_proposals]
    write_jsonl(proposals_path, proposals)
    ledger_written = False if no_ledger else append_ops(
        ops_ledger,
        candidate_count=len(candidates),
        report=report_path,
        proposals=proposals_path,
    )
    return {
        "candidates": len(candidates),
        "proposals": len(proposals),
        "top": candidates[0].name if candidates else "",
        "provider_mode": str(payload.get("provider_mode") or ("fixture" if fixture_path else "seed")),
        "report": str(report_path),
        "proposal_file": str(proposals_path),
        "ledger_written": ledger_written,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank tool/model adoption discoveries.")
    parser.add_argument("--focus", default="self-standing FPOS build loop tools and model replacements")
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--proposals", type=Path, default=DEFAULT_PROPOSALS)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--max-proposals", type=int, default=5)
    parser.add_argument("--live", action="store_true", help="Search live GitHub sources before falling back to seeds.")
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        summary = run(
            focus=args.focus,
            fixture_path=args.fixture,
            report_path=args.report,
            proposals_path=args.proposals,
            ops_ledger=args.ops_ledger,
            no_ledger=args.no_ledger,
            max_proposals=args.max_proposals,
            live=args.live,
        )
        code = 0
    except ToolScoutError as exc:
        summary = {"status": "stalled", "reason": str(exc)}
        code = 2
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"tool-scout: {summary}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
