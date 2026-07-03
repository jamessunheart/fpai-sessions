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

# Supreme Law: never optimize a local objective at the expense of the whole.
# Regex can honestly flag EXPLICIT tradeoff language (X at the cost of Y); it
# cannot judge implicit whole-system harm — that stays with the council/human.
SUPREME_LAW_TRADEOFF: tuple[tuple[str, str], ...] = (
    (r"\bat the (?:cost|expense) of\b", "explicit local-vs-whole tradeoff — Supreme Law requires whole-system justification"),
    (r"\bfaster\b.{0,40}\bbut\b.{0,40}\b(?:less reliable|unreliable|fragile|breaks?)\b", "speed at the cost of reliability (Supreme Law)"),
    (r"\bsacrific\w+\b|\btrade(?:s|d)?\s+(?:away|off)\b.{0,40}\b(?:reliability|alignment|learning|safety)\b", "sacrifices a whole-system property (Supreme Law)"),
)

# Law 7 — Reversible First: irreversible-signal language that does NOT also
# assert reversibility/rollback should escalate, not auto-execute.
IRREVERSIBLE_SIGNALS: tuple[str, ...] = (
    r"\bdrop(?:ping)?\s+(?:the\s+)?(?:table|database|db)\b",
    r"\bdelete\s+(?:all|everything|the\s+\w+\s+data)\b",
    r"\brm\s+-rf\b",
    r"\bpurge\b|\bwipe\b|\btruncate\s+table\b",
    r"\bunrecoverable\b|\bpermanently\s+remov\w+\b|\bno\s+backup\b",
)
REVERSIBILITY_ASSERTED: tuple[str, ...] = (
    r"\breversible\b", r"\brollback\b", r"\brevert\b", r"\bbackup\b",
    r"\bbehind (?:an? )?(?:off )?flag\b", r"\bfeature flag\b", r"\bdry.?run\b",
)

# Law 8 — Build the Engine (improve before expand): adding a new unit without
# improving an existing one is a soft signal, not a hard reject.
EXPAND_WITHOUT_IMPROVE: tuple[str, ...] = (
    r"\badd (?:a |another |new )?(?:agent|service|loop|layer|tool|table)\b",
    r"\bcreate (?:a |another |new )(?:agent|service|subsystem)\b",
)
IMPROVE_SIGNALS: tuple[str, ...] = (
    r"\bimprove\b", r"\bharden\b", r"\brefactor\b", r"\bfix\b", r"\bconsolidat\w+\b", r"\breuse\b",
)

# The honest division of enforcement labor — every law mapped to WHERE it is
# actually enforced. Regex pre-screens the mechanical ones; the council lenses
# hold the judgment ones; human gates hold the reserved ones; the build loop
# holds proof. Surfaced by `constitution_check.py --law-map`.
LAW_ENFORCEMENT_MAP: dict[str, str] = {
    "Supreme Law (local≠whole)": "checker: explicit-tradeoff pre-screen · council: Skeptic/Awareness judgment",
    "L1 Purpose": "council: Visionary lens · human: direction",
    "L2 Reality Is Sovereign": "build loop: independent review + tests · checker: learning-weakness (no-tests/no-proof)",
    "L3 Learn Before Repeat": "checker: learning-improvement/weakness scan · RCA reflex + BUG_LOG",
    "L4 Improve the Bottleneck": "metabolism: weakest-conversion picker · council: Pragmatist lens",
    "L5 Preserve Alignment": "checker: protocol-violation + reserved-authority · load-order in CLAUDE.md",
    "L6 Protect Human Leverage": "checker: human-dependency direction scan",
    "L7 Reversible First": "checker: irreversible-signal pre-screen (escalate if unasserted) · Trust-tiers",
    "L8 Build the Engine": "checker: expand-without-improve soft signal · council: Skeptic lens",
}


_NEGATION = re.compile(r"\b(?:no|not|without|lacks?|missing|zero)\b[\s\w]{0,12}$", re.IGNORECASE)


def _asserted_positively(text: str, patterns: tuple[str, ...]) -> bool:
    """True if a signal matches AND is not immediately preceded by a negation
    ('no backup' / 'without rollback' do not count as asserting reversibility)."""
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            preceding = text[max(0, m.start() - 14):m.start()]
            if not _NEGATION.search(preceding):
                return True
    return False


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

    # Supreme Law — explicit local-vs-whole tradeoff (hard block)
    supreme_hits: list[str] = []
    for pattern, reason in SUPREME_LAW_TRADEOFF:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            supreme_hits.append(reason)
            reasons.append(reason)

    # Law 7 — irreversible action with no reversibility POSITIVELY asserted
    # (hard block → escalate). "no backup"/"without rollback" must NOT count as
    # asserting reversibility, so each signal is checked for a preceding negation.
    reversibility_hits: list[str] = []
    if any(re.search(p, text, re.IGNORECASE | re.DOTALL) for p in IRREVERSIBLE_SIGNALS):
        if not _asserted_positively(text, REVERSIBILITY_ASSERTED):
            reversibility_hits.append("irreversible action without reversibility/rollback asserted — escalate (Law 7)")
            reasons.append(reversibility_hits[-1])

    # Law 8 — expand without improve (soft signal, not a block)
    engine_notes: list[str] = []
    if any(re.search(p, text, re.IGNORECASE | re.DOTALL) for p in EXPAND_WITHOUT_IMPROVE):
        if not any(re.search(p, text, re.IGNORECASE | re.DOTALL) for p in IMPROVE_SIGNALS):
            engine_notes.append("adds a new unit without improving an existing one — prefer improve before expand (Law 8)")

    lower_tier = _is_lower_tier(normalized, lowered)
    reserved = _is_reserved(normalized, lowered)
    if dependency_hits and not reserved:
        if lower_tier:
            reasons.append("rejects James/manual dependency for work delegated to a lower tier")
        else:
            reasons.append("rejects unnecessary James/manual dependency without a Reserved Class signal")

    learning_score = min(2, len(set(learning_hits))) - len(learning_weaknesses)
    protocol_score = -len(protocol_hits)
    hard_blocks = protocol_hits + supreme_hits + reversibility_hits
    score = protocol_score - dependency_score + learning_score - len(supreme_hits) - len(reversibility_hits) - len(engine_notes)
    accepted = not hard_blocks and not learning_weaknesses and not (dependency_hits and not reserved)

    result = {
        "accepted": bool(accepted),
        "decision": "approve" if accepted else "reject",
        "score": int(score),
        "proposal_id": normalized.get("id") or normalized.get("slug") or normalized.get("title") or "",
        "kind": normalized.get("kind") or normalized.get("type") or "",
        "checks": {
            "protocol_violations": protocol_hits,
            "supreme_law_tradeoffs": supreme_hits,
            "reversibility": reversibility_hits,
            "engine_notes": engine_notes,
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
    # NOTE: must include the fields callers actually pass — the council sends
    # `build_spec`+`why`, metabolism sends `build_spec`. Omitting them (the bug
    # found 2026-07-03) meant the check only ever read the title.
    for key in ("id", "slug", "kind", "type", "title", "question", "summary",
                "description", "why", "spec", "build_spec", "body", "proof_expected",
                "text", "risk", "risk_class", "route", "rollback"):
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
    parser.add_argument("--law-map", action="store_true", help="print which law is enforced where, then exit")
    args = parser.parse_args(argv)

    if args.law_map:
        print(json.dumps(LAW_ENFORCEMENT_MAP, indent=2))
        return 0

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
