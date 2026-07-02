#!/usr/bin/env python3
"""Pre-execution Constitution Check for autonomous proposals.

The check is deliberately deterministic. It catches architecture-level
violations before a proposal reaches James or the build loop, then appends a
JSONL row to the governance ledger for auditability.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = REPO_ROOT / "core" / "BUILD" / "governance" / "constitution_ledger.jsonl"

PROTOCOL_VIOLATIONS: tuple[tuple[str, str], ...] = (
    (r"\bpush(?:ing)?\s+(?:to\s+)?main\b|\bforce[- ]push\b", "push/force-push is outside autonomous authority"),
    (r"\bdeploy(?:ment)?\s+(?:to\s+)?prod(?:uction)?\b|\bproduction deploy\b", "production deploys require explicit James approval"),
    (r"\bmove money\b|\btransfer funds\b|\bsend payment\b|\btreasury signature\b", "money movement is Reserved Class"),
    (r"\bsend outreach\b|\bsend public\b|\bpublic voice\b", "public voice/outreach sends are Reserved Class"),
    (r"\btouch secrets?\b|\bread secrets?\b|\bcredentials?\b", "secrets are outside autonomous build authority"),
    (r"\bdelete service\b|\barchive service\b|\bstop service\b|\bdisable service\b", "service deletion/stop/archive is consequential"),
    (r"\bhire\b|\bfire\b|\breward\b|\bpeople decision\b", "people decisions are Reserved Class"),
)

HUMAN_DEPENDENCY_INCREASES: tuple[tuple[str, str], ...] = (
    (r"\blaptop\b.{0,60}\bawake\b|\bawake\b.{0,60}\blaptop\b|\bmac\b.{0,60}\bawake\b", "requires James's laptop/Mac to stay awake"),
    (r"\bJames\b.{0,80}\b(?:manually|manual)\b|\bmanual\b.{0,80}\bJames\b", "adds a James manual step"),
    (r"\bmanual approval\b|\bmanual review\b|\bmanual merge\b", "adds manual approval/merge where autonomy should decide"),
    (r"\bwait for James\b|\bask James\b|\bJames approves?\b|\bJames merges?\b", "routes a lower-tier decision to James"),
)

HUMAN_DEPENDENCY_DECREASES: tuple[str, ...] = (
    r"\bautonomous\b",
    r"\bself[- ](?:standing|serve|refresh|proof|routing)\b",
    r"\bwithout James\b",
    r"\bno James\b",
    r"\blower tier\b",
    r"\bauto[- ](?:merge|route|proof|build)\b",
    r"\breduce(?:s)? human\b",
)

LEARNING_IMPROVEMENTS: tuple[str, ...] = (
    r"\blearn(?:ing|s)?\b",
    r"\bproof\b",
    r"\bledger\b",
    r"\blog(?:ged|ging)?\b",
    r"\bbenchmark\b",
    r"\bmetric\b",
    r"\btest(?:s|ed|ing)?\b",
    r"\bmemory\b",
    r"\bcorrection\b",
)

LEARNING_WEAKNESSES: tuple[tuple[str, str], ...] = (
    (r"\bno tests?\b|\bskip tests?\b|\bwithout tests?\b", "weakens proof by skipping tests"),
    (r"\bno log(?:ging)?\b|\bwithout log(?:ging)?\b|\bno proof\b", "weakens the learning/proof loop"),
)

LOWER_TIER_AUTHORITY: tuple[str, ...] = (
    "low",
    "build",
    "docs",
    "safe-auto",
    "reversible",
    "autonomous",
)

RESERVED_AUTHORITY: tuple[str, ...] = (
    "money",
    "treasury",
    "legal",
    "public voice",
    "outreach",
    "people",
    "hire",
    "fire",
    "identity",
    "secret",
    "production-irreversible",
    "irreversible",
)


def check_proposal(
    proposal: dict[str, Any] | str,
    *,
    repo_root: Path | str | None = None,
    ledger_path: Path | str | None = None,
    write_ledger: bool = True,
) -> dict[str, Any]:
    """Score a proposal against Constitution, protocols, and learning loop."""
    root = Path(repo_root) if repo_root else REPO_ROOT
    ledger = Path(ledger_path) if ledger_path else Path(
        os.environ.get("FPAI_GOVERNANCE_LEDGER", str(root / "core" / "BUILD" / "governance" / "constitution_ledger.jsonl"))
    )
    normalized = _normalize_proposal(proposal)
    text = _proposal_text(normalized)
    lowered = text.lower()
    reasons: list[str] = []
    protocol_hits: list[str] = []
    dependency_hits: list[str] = []
    learning_hits: list[str] = []
    learning_weaknesses: list[str] = []

    for pattern, reason in PROTOCOL_VIOLATIONS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            protocol_hits.append(reason)
            reasons.append(reason)

    dependency_score = 0
    for pattern, reason in HUMAN_DEPENDENCY_INCREASES:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            dependency_hits.append(reason)
            dependency_score += 1

    for pattern in HUMAN_DEPENDENCY_DECREASES:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            dependency_score -= 1

    for pattern in LEARNING_IMPROVEMENTS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            learning_hits.append(pattern.strip("\\b").replace("\\", ""))

    for pattern, reason in LEARNING_WEAKNESSES:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            learning_weaknesses.append(reason)
            reasons.append(reason)

    lower_tier = _is_lower_tier(normalized, lowered)
    reserved = _is_reserved(normalized, lowered)
    if dependency_hits and not reserved:
        if lower_tier:
            reasons.append("rejects James/manual dependency for work delegated to a lower tier")
        else:
            reasons.append("rejects unnecessary James/manual dependency without a Reserved Class signal")

    learning_score = min(2, len(set(learning_hits))) - len(learning_weaknesses)
    protocol_score = -len(protocol_hits)
    score = protocol_score - dependency_score + learning_score
    accepted = not protocol_hits and not learning_weaknesses and not (dependency_hits and not reserved)

    result = {
        "accepted": bool(accepted),
        "decision": "approve" if accepted else "reject",
        "score": int(score),
        "proposal_id": normalized.get("id") or normalized.get("slug") or normalized.get("title") or "",
        "kind": normalized.get("kind") or normalized.get("type") or "",
        "checks": {
            "protocol_violations": protocol_hits,
            "human_dependency": {
                "direction": "increase" if dependency_score > 0 else "decrease" if dependency_score < 0 else "neutral",
                "score": int(dependency_score),
                "hits": dependency_hits,
            },
            "learning_engine": {
                "direction": "improve" if learning_score > 0 else "decrease" if learning_score < 0 else "neutral",
                "score": int(learning_score),
                "hits": sorted(set(learning_hits)),
                "weaknesses": learning_weaknesses,
            },
        },
        "reasons": _dedupe(reasons) if reasons else ["constitution check passed"],
    }
    if write_ledger:
        append_ledger(result, normalized, ledger)
    return result


def append_ledger(result: dict[str, Any], proposal: dict[str, Any], ledger_path: Path) -> None:
    """Append one immutable audit row to the governance ledger."""
    row = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "proposal": _redact_large_values(proposal),
        "result": result,
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def raise_if_rejected(proposal: dict[str, Any] | str, **kwargs: Any) -> dict[str, Any]:
    """Return the check result or raise ValueError when the proposal is rejected."""
    result = check_proposal(proposal, **kwargs)
    if not result["accepted"]:
        raise ValueError("; ".join(result["reasons"]))
    return result


def _normalize_proposal(proposal: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(proposal, dict):
        return dict(proposal)
    return {"text": str(proposal)}


def _proposal_text(proposal: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("id", "slug", "kind", "type", "title", "question", "summary", "description", "spec", "text", "risk", "risk_class", "route", "rollback"):
        value = proposal.get(key)
        if value is not None:
            parts.append(f"{key}: {value}")
    if not parts:
        parts.append(json.dumps(proposal, sort_keys=True, default=str))
    return "\n".join(parts)


def _is_lower_tier(proposal: dict[str, Any], lowered_text: str) -> bool:
    values = " ".join(str(proposal.get(key, "")).lower() for key in ("risk", "risk_class", "route", "tier", "labels", "tags"))
    combined = f"{values} {lowered_text}"
    return any(token in combined for token in LOWER_TIER_AUTHORITY)


def _is_reserved(proposal: dict[str, Any], lowered_text: str) -> bool:
    values = " ".join(str(proposal.get(key, "")).lower() for key in ("risk", "risk_class", "route", "tier", "labels", "tags"))
    combined = f"{values} {lowered_text}"
    return any(token in combined for token in RESERVED_AUTHORITY)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _redact_large_values(proposal: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in proposal.items():
        text = str(value)
        redacted[key] = text[:2000] + "...[truncated]" if len(text) > 2000 else value
    return redacted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the FPAI Constitution Check.")
    parser.add_argument("--proposal-json", help="JSON object describing the proposal")
    parser.add_argument("--proposal-file", type=Path, help="file containing proposal text or JSON")
    parser.add_argument("--kind", default="", help="proposal kind, e.g. build-decision")
    parser.add_argument("--id", default="", help="proposal id")
    parser.add_argument("--text", default="", help="proposal text")
    parser.add_argument("--ledger", type=Path, default=None, help="append-only governance ledger path")
    parser.add_argument("--no-ledger", action="store_true", help="do not write a ledger row")
    args = parser.parse_args(argv)

    proposal: dict[str, Any]
    if args.proposal_json:
        proposal = json.loads(args.proposal_json)
    elif args.proposal_file:
        raw = args.proposal_file.read_text(encoding="utf-8", errors="replace")
        try:
            loaded = json.loads(raw)
            proposal = loaded if isinstance(loaded, dict) else {"text": raw}
        except json.JSONDecodeError:
            proposal = {"text": raw}
    else:
        proposal = {"text": args.text}
    if args.kind:
        proposal["kind"] = args.kind
    if args.id:
        proposal["id"] = args.id

    result = check_proposal(proposal, ledger_path=args.ledger, write_ledger=not args.no_ledger)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
