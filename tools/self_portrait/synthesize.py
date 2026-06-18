#!/usr/bin/env python3
"""Synthesize the system self-portrait from observable repo/local evidence.

The portrait is intentionally evidence-bounded. Missing private DB/log sources
become named blind spots instead of guessed self-knowledge.
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

REPO = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_MODEL_DNA = REPO / "core" / "STATE" / "MODEL_DNA.md"
DEFAULT_SELF_PORTRAIT = REPO / "core" / "STATE" / "SELF_PORTRAIT.md"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_CONSCIOUSNESS_DIR = Path(os.environ.get("FPAI_CONSCIOUSNESS_DIR", Path.home() / ".config" / "fpai" / "consciousness"))
DEFAULT_SCOUT_LOG = Path(os.environ.get("SCOUT_LOG", str(REPO / "core" / "BUILD" / "signals" / "tool_scout_proposals.jsonl")))
MAX_CONTEXT_CHARS = 5000
PERSONAL_PATTERNS = (
    re.compile(r"\bJames\b", re.IGNORECASE),
    re.compile(r"\btelegram\b", re.IGNORECASE),
    re.compile(r"\bemail\b", re.IGNORECASE),
    re.compile(r"\bphone\b", re.IGNORECASE),
    re.compile(r"\bcontact\b", re.IGNORECASE),
    re.compile(r"\btreasury\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class PortraitEvidence:
    model_dna_signals: tuple[str, ...]
    ops_counts: dict[str, int]
    recent_ops: tuple[str, ...]
    consciousness_index: int | None
    consciousness_observations: tuple[str, ...]
    scout_count: int
    review_counts: dict[str, int]
    unavailable_sources: tuple[str, ...]


def utc_stamp(now: dt.datetime | None = None) -> str:
    return (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_jsonl(path: Path, *, limit: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _clean_public_line(line: str, *, max_len: int = 180) -> str:
    line = re.sub(r"\s+", " ", line.strip(" -*\t|"))
    line = re.sub(r"\*\*", "", line)
    for pattern in PERSONAL_PATTERNS:
        line = pattern.sub("[personal]", line)
    return line[:max_len]


def model_dna_signals(path: Path = DEFAULT_MODEL_DNA, *, limit: int = 6) -> tuple[str, ...]:
    text = read_text(path)
    if not text:
        return ()
    signals: list[str] = []
    for raw in text.splitlines():
        line = _clean_public_line(raw)
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        if line.lower().startswith(("what this is:", "last updated:", "next council review:")):
            continue
        if any(key in line.lower() for key in ("signals weighted", "skeptic", "awareness", "routing", "council", "outcome")):
            if line not in signals:
                signals.append(line)
        if len(signals) >= limit:
            break
    return tuple(signals)


def latest_consciousness(consciousness_dir: Path = DEFAULT_CONSCIOUSNESS_DIR) -> tuple[int | None, tuple[str, ...]]:
    try:
        from tools.consciousness import loop as consciousness_loop
    except Exception:
        return None, ()
    obs = consciousness_loop.latest_observation(consciousness_dir)
    if not obs:
        return None, ()
    return obs.awareness_index, tuple(_clean_public_line(item) for item in obs.top_observations if _clean_public_line(item))


def summarize_ops(path: Path = DEFAULT_OPS_LEDGER) -> tuple[dict[str, int], tuple[str, ...]]:
    rows = read_jsonl(path)
    counts: dict[str, int] = {}
    recent: list[str] = []
    for row in rows:
        event = str(row.get("event") or "?")
        counts[event] = counts.get(event, 0) + 1
    for row in rows[-5:]:
        loop = _clean_public_line(str(row.get("loop") or "?"), max_len=40)
        event = _clean_public_line(str(row.get("event") or "?"), max_len=40)
        detail = _clean_public_line(str(row.get("detail") or ""), max_len=90)
        if detail:
            recent.append(f"{loop}: {event} - {detail}")
        else:
            recent.append(f"{loop}: {event}")
    return counts, tuple(recent)


def summarize_reviews(review_dir: Path = REPO / "core" / "BUILD" / "reviews") -> dict[str, int]:
    counts = {"approved": 0, "blocked": 0, "risk": 0, "files": 0}
    if not review_dir.exists():
        return counts
    for path in list(review_dir.glob("*.md"))[-200:]:
        text = read_text(path).lower()
        if not text:
            continue
        counts["files"] += 1
        if "approved" in text or "no remaining p1" in text or "no remaining p2" in text:
            counts["approved"] += 1
        if "blocked" in text or "blocker" in text:
            counts["blocked"] += 1
        if "risk" in text:
            counts["risk"] += 1
    return counts


def collect_evidence(
    *,
    model_dna: Path = DEFAULT_MODEL_DNA,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    consciousness_dir: Path = DEFAULT_CONSCIOUSNESS_DIR,
    scout_log: Path = DEFAULT_SCOUT_LOG,
) -> PortraitEvidence:
    unavailable: list[str] = []
    dna = model_dna_signals(model_dna)
    if not dna:
        unavailable.append("MODEL_DNA.md")
    ops_counts, recent_ops = summarize_ops(ops_ledger)
    if not ops_counts:
        unavailable.append("ops_ledger.jsonl")
    awareness_index, observations = latest_consciousness(consciousness_dir)
    if awareness_index is None and not observations:
        unavailable.append("consciousness-observer logs")
    scout_rows = read_jsonl(scout_log)
    if not scout_rows:
        unavailable.append("scout_log.jsonl")
    unavailable.extend(["brain_index.corrections", "brain_index.thread", "brain_index.decisions"])
    return PortraitEvidence(
        model_dna_signals=dna,
        ops_counts=ops_counts,
        recent_ops=recent_ops,
        consciousness_index=awareness_index,
        consciousness_observations=observations,
        scout_count=len(scout_rows),
        review_counts=summarize_reviews(),
        unavailable_sources=tuple(dict.fromkeys(unavailable)),
    )


def _bullets(items: tuple[str, ...] | list[str], empty: str) -> list[str]:
    if not items:
        return [f"- {empty}"]
    return [f"- {item}" for item in items]


def render_portrait(evidence: PortraitEvidence, *, generated_at: str | None = None) -> str:
    generated = generated_at or utc_stamp()
    ops_total = sum(evidence.ops_counts.values())
    success_events = evidence.ops_counts.get("succeeded", 0) + evidence.ops_counts.get("merged", 0)
    failed_events = evidence.ops_counts.get("failed", 0) + evidence.ops_counts.get("error", 0)
    review_total = evidence.review_counts.get("files", 0)
    approved = evidence.review_counts.get("approved", 0)
    blocked = evidence.review_counts.get("blocked", 0)
    awareness = "unknown" if evidence.consciousness_index is None else f"{evidence.consciousness_index}/100"
    gap = [
        "The stated model emphasizes outcome proof, skepticism, and routing discipline; the observable system still needs explicit instrumentation to notice when it is performing coherence instead of proving it.",
        f"Evidence base is uneven: {ops_total} recent ops-ledger rows and {review_total} review files are visible, while correction/thread/decision database rows are unavailable in this repo-only run.",
        "The gap to improve is not more confident self-description; it is tighter comparison between claimed heuristics and measured correction, decision, review, and observer outcomes.",
    ]
    trajectory = [
        f"Throughput is visible through ops events ({success_events} success-like, {failed_events} failure-like in the sampled ledger).",
        f"Build review memory is present ({approved} approval-like, {blocked} blocker-like files in the sampled review set).",
        f"Observer calibration is {'available at ' + awareness if evidence.consciousness_index is not None else 'not available in this environment'}.",
    ]
    lines = [
        "# Self-Portrait",
        "",
        "classification: COUNCIL-OPEN",
        "privacy: public-tier synthesis only; no personal names, contact details, private messages, secrets, or treasury values",
        "generated_by: d102 self-portrait synthesis agent",
        f"generated_at: {generated}",
        "version: v1",
        "",
        "## Who I think I am",
        "",
        *_bullets(evidence.model_dna_signals, "MODEL_DNA was unavailable, so stated self-model evidence could not be read."),
        "",
        "## What the evidence shows",
        "",
        f"- Ops-ledger sample: {ops_total} rows; event counts: {json.dumps(evidence.ops_counts, sort_keys=True)}.",
        f"- Build reviews sampled: {review_total}; approval-like: {approved}; blocker-like: {blocked}; risk mentions: {evidence.review_counts.get('risk', 0)}.",
        f"- Consciousness observer awareness index: {awareness}.",
        f"- Scout rows visible: {evidence.scout_count}.",
        "",
        "Recent ops signals:",
        *_bullets(evidence.recent_ops, "No recent ops rows were readable from this environment."),
        "",
        "Observer signals:",
        *_bullets(evidence.consciousness_observations, "No observer observations were readable from this environment."),
        "",
        "## The gap",
        "",
        *_bullets(gap, "No gap could be computed."),
        "",
        "## What I'm becoming",
        "",
        *_bullets(trajectory, "Trajectory evidence unavailable."),
        "",
        "## Blind spots (unobservable)",
        "",
        *_bullets(list(evidence.unavailable_sources), "No blind spots named."),
        "",
        "## Version history",
        "",
        "| Version | Date | Synthesizer | Evidence summary |",
        "|---|---|---|---|",
        f"| v1 | {generated[:10]} | d102 self-portrait synthesis agent | ops={ops_total}; reviews={review_total}; awareness={awareness}; scout={evidence.scout_count} |",
        "",
        "<!-- Council synthesis appends future versions below this line. -->",
        "",
    ]
    return "\n".join(lines)


def self_portrait_context(path: Path = DEFAULT_SELF_PORTRAIT, *, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    text = read_text(path)
    if not text:
        return ""
    sections = []
    for heading in ("What the evidence shows", "The gap", "What I'm becoming", "Blind spots (unobservable)"):
        match = re.search(rf"^## {re.escape(heading)}\s*$", text, flags=re.MULTILINE)
        if not match:
            continue
        start = match.end()
        next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(text)
        body = text[start:end].strip()
        if body:
            sections.append(f"## {heading}\n{body}")
    if not sections:
        return text[:max_chars]
    return ("SELF-PORTRAIT CONTEXT - COUNCIL-OPEN\n" + "\n\n".join(sections))[:max_chars]


def write_portrait(path: Path = DEFAULT_SELF_PORTRAIT, *, evidence: PortraitEvidence | None = None, generated_at: str | None = None) -> str:
    portrait = render_portrait(evidence or collect_evidence(), generated_at=generated_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(portrait, encoding="utf-8")
    return portrait


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesize core/STATE/SELF_PORTRAIT.md.")
    parser.add_argument("--output", default=str(DEFAULT_SELF_PORTRAIT))
    parser.add_argument("--context", action="store_true", help="Print bounded context instead of writing.")
    args = parser.parse_args(argv)
    output = Path(args.output)
    if args.context:
        print(self_portrait_context(output))
        return 0
    portrait = write_portrait(output)
    print(f"wrote {output} ({len(portrait)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
