#!/usr/bin/env python3
"""Watch whether claimed unlocks actually realized.

This module records and reports consequences only. It never edits the
buildstream, changes weights, dispatches work, or resolves gates.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_HANDOFF = REPO_ROOT / "docs" / "codex" / "HANDOFF.md"
DEFAULT_REPORT = REPO_ROOT / "docs" / "codex" / "CONSEQUENCE_REPORT.md"
DEFAULT_QUEUE = REPO_ROOT / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
DEFAULT_RESULTS_LEDGER = REPO_ROOT / "core" / "STATE" / "RESULTS_DRAFTS" / "consequence.jsonl"
DEFAULT_APPRENTICE_LEDGER = REPO_ROOT / "tools" / "apprentice" / "runs" / "apprentice_review_ledger.jsonl"
DEFAULT_LOCAL_PROOF = Path.home() / ".claude" / "memory-global" / "PROOF_LOG.md"
DEFAULT_VAULT_PROOF = Path(
    os.environ.get(
        "FPAI_VAULT",
        Path.home()
        / "Library"
        / "Mobile Documents"
        / "iCloud~md~obsidian"
        / "Documents"
        / "FPOS"
        / "Full Potential OS",
    )
) / "00_MEMORY" / "PROOF LOG.md"

VERDICTS = {"realized", "not-yet", "no"}
STOPWORDS = {
    "about",
    "after",
    "again",
    "build",
    "builds",
    "built",
    "check",
    "codex",
    "first",
    "from",
    "gate",
    "gates",
    "intent",
    "james",
    "move",
    "next",
    "proof",
    "ready",
    "review",
    "route",
    "system",
    "that",
    "this",
    "with",
}


@dataclasses.dataclass(frozen=True)
class ProofClaim:
    source: str
    row_id: str
    intent_solved: str
    unlock_claimed: str
    proof: str = ""
    next_move: str = ""


@dataclasses.dataclass(frozen=True)
class ConsequenceVerdict:
    claim: ProofClaim
    verdict: str
    confidence: float
    evidence: list[str]
    proposal: str


def default_markdown_sources() -> list[Path]:
    """Return readable proof-like Markdown sources, newest local surfaces first."""
    return [path for path in (DEFAULT_HANDOFF, DEFAULT_LOCAL_PROOF, DEFAULT_VAULT_PROOF) if path.exists()]


def load_markdown_claims(paths: list[Path | str] | None = None, *, limit: int | None = None) -> list[ProofClaim]:
    """Parse proof claims from Markdown proof rows and Codex handoff close-outs."""
    claims: list[ProofClaim] = []
    for raw_path in paths or default_markdown_sources():
        path = Path(raw_path)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        claims.extend(_proof_log_claims(path, text))
        claims.extend(_handoff_claims(path, text))
    return claims[:limit] if limit else claims


def _proof_log_claims(path: Path, text: str) -> list[ProofClaim]:
    claims: list[ProofClaim] = []
    pattern = re.compile(
        r"Intent solved:\s*(?P<intent>.*?)\s*"
        r"(?:·|\|)\s*Unlocks next:\s*(?P<unlock>.*?)\s*"
        r"(?:(?:·|\|)\s*Proof:\s*(?P<proof>.*?))?"
        r"(?:(?:·|\|)\s*Next move:\s*(?P<next>.*?))?"
        r"(?:\s*(?:·|\|)\s*AI|\s*$)",
        re.IGNORECASE,
    )
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = pattern.search(line)
        if not match:
            continue
        claims.append(
            ProofClaim(
                source=str(path),
                row_id=f"{path.name}:{line_no}",
                intent_solved=_clean(match.group("intent")),
                unlock_claimed=_clean(match.group("unlock")),
                proof=_clean(match.group("proof") or ""),
                next_move=_clean(match.group("next") or ""),
            )
        )
    return claims


def _handoff_claims(path: Path, text: str) -> list[ProofClaim]:
    claims: list[ProofClaim] = []
    blocks = re.split(r"\n(?=### )", text)
    for block in blocks:
        heading = block.splitlines()[0].strip() if block.strip() else ""
        intent = _field_from_block(block, "Intent solved")
        unlock = _field_from_block(block, "Downstream intent unlocked") or _field_from_block(block, "Unlocks next")
        if not intent or not unlock:
            continue
        proof = _field_from_block(block, "Tests") or _field_from_block(block, "Proof")
        next_move = _field_from_block(block, "Questions for Ember/James")
        claims.append(
            ProofClaim(
                source=str(path),
                row_id=heading.lstrip("# ").strip() or path.name,
                intent_solved=intent,
                unlock_claimed=unlock,
                proof=proof,
                next_move=next_move,
            )
        )
    return claims


def _field_from_block(block: str, label: str) -> str:
    pattern = re.compile(rf"^- \*\*{re.escape(label)}:\*\*\s*(?P<value>.+)$", re.MULTILINE)
    match = pattern.search(block)
    return _clean(match.group("value")) if match else ""


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    ledger = Path(path)
    if not ledger.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {ledger}:{line_no}") from exc
    return rows


def load_queue(path: Path | str = DEFAULT_QUEUE) -> dict[str, Any]:
    qpath = Path(path)
    if not qpath.exists():
        return {"version": 1, "gates": []}
    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid queue JSON: {qpath}") from exc
    gates = data.get("gates", [])
    if not isinstance(gates, list):
        raise ValueError("queue JSON must contain a gates list")
    return {"version": data.get("version", 1), "gates": gates}


def verdict_for_claim(
    claim: ProofClaim,
    *,
    repo_root: Path | str = REPO_ROOT,
    queue: dict[str, Any] | None = None,
    consequence_rows: list[dict[str, Any]] | None = None,
    apprentice_rows: list[dict[str, Any]] | None = None,
) -> ConsequenceVerdict:
    """Return a conservative consequence verdict for one claimed unlock."""
    repo = Path(repo_root)
    queue = queue or {"gates": []}
    consequence_rows = consequence_rows or []
    apprentice_rows = apprentice_rows or []
    text = " ".join([claim.intent_solved, claim.unlock_claimed, claim.proof, claim.next_move])

    evidence: list[str] = []
    result_evidence = _result_evidence(text, consequence_rows)
    if result_evidence:
        verdict, detail = result_evidence
        return _verdict(claim, verdict, 0.86 if verdict == "realized" else 0.74, [detail])

    gate_evidence = _gate_evidence(text, queue)
    if gate_evidence:
        verdict, detail = gate_evidence
        confidence = 0.84 if verdict == "realized" else 0.62
        return _verdict(claim, verdict, confidence, [detail])

    for artifact in artifact_candidates(text):
        path = repo / artifact
        if path.exists():
            evidence.append(f"artifact exists: `{artifact}`")
    if evidence:
        return _verdict(claim, "realized", 0.82, evidence)

    apprentice_evidence = _apprentice_evidence(text, apprentice_rows)
    if apprentice_evidence:
        verdict, detail = apprentice_evidence
        return _verdict(claim, verdict, 0.68 if verdict == "realized" else 0.56, [detail])

    return _verdict(claim, "not-yet", 0.42, ["no observable evidence found yet"])


def analyze(
    claims: list[ProofClaim],
    *,
    repo_root: Path | str = REPO_ROOT,
    queue_path: Path | str = DEFAULT_QUEUE,
    consequence_ledger_path: Path | str = DEFAULT_RESULTS_LEDGER,
    apprentice_ledger_path: Path | str = DEFAULT_APPRENTICE_LEDGER,
) -> list[ConsequenceVerdict]:
    queue = load_queue(queue_path)
    consequence_rows = load_jsonl(consequence_ledger_path)
    apprentice_rows = load_jsonl(apprentice_ledger_path)
    return [
        verdict_for_claim(
            claim,
            repo_root=repo_root,
            queue=queue,
            consequence_rows=consequence_rows,
            apprentice_rows=apprentice_rows,
        )
        for claim in claims
    ]


def summarize(verdicts: list[ConsequenceVerdict]) -> dict[str, Any]:
    counts = {verdict: 0 for verdict in sorted(VERDICTS)}
    for item in verdicts:
        counts[item.verdict] += 1
    total = len(verdicts)
    realized_rate = (counts["realized"] / total) if total else 0.0
    recurring = _recurring_non_realizations(verdicts)
    return {
        "total_claims": total,
        "counts": counts,
        "realized_rate": realized_rate,
        "recurring_non_realizations": recurring,
        "next_improvement": next_improvement(verdicts, recurring),
        "weight_proposals": weight_proposals(verdicts),
    }


def next_improvement(verdicts: list[ConsequenceVerdict], recurring: list[dict[str, Any]]) -> str:
    if not verdicts:
        return "Record proof rows with Intent solved and Unlocks next fields before consequence learning can start."
    if recurring:
        top = recurring[0]
        return (
            f"Review `{top['unlock']}` first: it is still unrealized across {top['count']} claim(s). "
            "Either close the evidence gap or stop claiming that unlock."
        )
    not_yet = [item for item in verdicts if item.verdict == "not-yet"]
    if not_yet:
        return f"Add concrete evidence for `{not_yet[0].claim.unlock_claimed}` or revise the claimed unlock."
    return "Most checked unlocks have observable evidence; keep routing the next adjacent proof loop."


def weight_proposals(verdicts: list[ConsequenceVerdict]) -> list[str]:
    proposals: list[str] = []
    for item in verdicts:
        if item.verdict == "realized":
            proposals.append(f"Proposal only: consider a small weight bump for work that unlocked `{item.claim.unlock_claimed}`.")
        elif item.verdict == "no":
            proposals.append(f"Proposal only: consider lowering/rephrasing work that failed `{item.claim.unlock_claimed}`.")
    return _dedupe(proposals)[:5]


def render_report(verdicts: list[ConsequenceVerdict]) -> str:
    summary = summarize(verdicts)
    stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "---",
        "generated: true",
        "source: tools/consequence/watch.py",
        f"last_generated: {stamp}",
        "edit_policy: regenerate, do not hand-edit",
        "---",
        "",
        "# Consequence Report",
        "",
        "*Records and proposals only. No buildstream weights, gates, sends, money, deploys, secrets, or live-loop wiring changed.*",
        "",
        "## Summary",
        "",
        f"- total claims: `{summary['total_claims']}`",
        f"- realized: `{summary['counts']['realized']}`",
        f"- not-yet: `{summary['counts']['not-yet']}`",
        f"- no: `{summary['counts']['no']}`",
        f"- realized rate: `{summary['realized_rate']:.0%}`",
        "",
        "## Next Improvement",
        "",
        summary["next_improvement"],
        "",
        "## Claims",
        "",
    ]
    if not verdicts:
        lines.append("_No proof claims found._")
    for item in verdicts:
        lines.extend(
            [
                f"### {item.claim.row_id}",
                f"- verdict: `{item.verdict}`",
                f"- confidence: `{item.confidence:.2f}`",
                f"- intent solved: {item.claim.intent_solved}",
                f"- unlock claimed: {item.claim.unlock_claimed}",
                "- evidence:",
            ]
        )
        lines.extend(f"  - {evidence}" for evidence in item.evidence)
        lines.append(f"- proposal: {item.proposal}")
        lines.append("")
    lines.extend(["## Recurring Non-Realizations", ""])
    recurring = summary["recurring_non_realizations"]
    if not recurring:
        lines.append("_None detected._")
    else:
        for row in recurring:
            lines.append(f"- `{row['unlock']}`: {row['count']} claim(s)")
    lines.extend(["", "## Weight Proposal Review Lane", ""])
    proposals = summary["weight_proposals"]
    if not proposals:
        lines.append("_No weight proposals._")
    else:
        lines.extend(f"- {proposal}" for proposal in proposals)
    lines.append("")
    return "\n".join(lines)


def write_report(verdicts: list[ConsequenceVerdict], path: Path | str = DEFAULT_REPORT, *, dry_run: bool = False) -> Path:
    report_path = Path(path)
    if dry_run:
        return report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(verdicts), encoding="utf-8")
    return report_path


def artifact_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for token in re.findall(r"`([^`]+)`", text):
        if _looks_like_repo_path(token):
            candidates.append(token)
    for token in re.findall(r"(?<![\w/.-])((?:tools|docs|core)/[\w./-]+)", text):
        if _looks_like_repo_path(token):
            candidates.append(token.rstrip(".,;)"))
    return _dedupe(candidates)


def _result_evidence(text: str, rows: list[dict[str, Any]]) -> tuple[str, str] | None:
    low = text.lower()
    for row in rows:
        key = str(row.get("opportunity_id") or row.get("intent_id") or "").lower()
        detail = str(row.get("detail") or row.get("outcome") or "").lower()
        if key and key not in low and key.replace("-", " ") not in low:
            continue
        if row.get("realized") is True:
            return "realized", f"result ledger realized `{row.get('outcome')}` for `{key}`"
        if row.get("realized") is False:
            return "no", f"result ledger recorded non-realized outcome `{row.get('outcome')}` for `{key or detail}`"
    return None


def _gate_evidence(text: str, queue: dict[str, Any]) -> tuple[str, str] | None:
    low = text.lower()
    for gate in queue.get("gates", []):
        gate_id = str(gate.get("id", ""))
        question = str(gate.get("question", ""))
        if not _gate_matches(low, gate_id, question):
            continue
        state = str(gate.get("state", "open"))
        if state == "answered":
            return "realized", f"human-edge gate `{gate_id}` answered `{gate.get('answer')}`"
        if state == "open":
            return "not-yet", f"human-edge gate `{gate_id}` is still open"
    return None


def _apprentice_evidence(text: str, rows: list[dict[str, Any]]) -> tuple[str, str] | None:
    low = text.lower()
    for row in rows:
        intent_id = str(row.get("intent_id") or "").lower()
        if not intent_id or intent_id not in low:
            continue
        if row.get("status") == "completed":
            return "realized", f"apprentice ledger completed `{intent_id}`"
        if row.get("status") == "gated":
            pause = row.get("would_pause_at") or "reserved step"
            return "not-yet", f"apprentice ledger still gated at `{pause}`"
    return None


def _verdict(claim: ProofClaim, verdict: str, confidence: float, evidence: list[str]) -> ConsequenceVerdict:
    proposal = {
        "realized": "Keep this unlock pattern; evidence exists.",
        "not-yet": "Check again after the next run or add concrete evidence.",
        "no": "Revise the claimed unlock or route a repair spec.",
    }[verdict]
    return ConsequenceVerdict(claim, verdict, confidence, evidence, proposal)


def _recurring_non_realizations(verdicts: list[ConsequenceVerdict]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in verdicts:
        if item.verdict == "realized":
            continue
        key = item.claim.unlock_claimed
        counts[key] = counts.get(key, 0) + 1
    rows = [{"unlock": key, "count": count} for key, count in counts.items() if count > 1]
    return sorted(rows, key=lambda row: (-row["count"], row["unlock"]))


def _looks_like_repo_path(token: str) -> bool:
    return token.startswith(("tools/", "docs/", "core/")) and not any(ch in token for ch in "\n\r\t ")


def _gate_matches(text: str, gate_id: str, question: str) -> bool:
    gate_id_low = gate_id.lower()
    if gate_id_low and gate_id_low in text:
        return True
    left_words = _significant_words(text)
    right_words = _significant_words(question)
    return len(left_words & right_words) >= 3


def _significant_words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9][a-z0-9-]+", text.lower())
        if len(word) > 3 and word not in STOPWORDS
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report whether proof unlocks realized.")
    parser.add_argument("--proof", type=Path, action="append", default=None, help="Markdown proof/handoff source")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--consequence-ledger", type=Path, default=DEFAULT_RESULTS_LEDGER)
    parser.add_argument("--apprentice-ledger", type=Path, default=DEFAULT_APPRENTICE_LEDGER)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", help="write nothing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    claims = load_markdown_claims(args.proof, limit=args.limit)
    verdicts = analyze(
        claims,
        queue_path=args.queue,
        consequence_ledger_path=args.consequence_ledger,
        apprentice_ledger_path=args.apprentice_ledger,
    )
    path = write_report(verdicts, args.report, dry_run=args.dry_run)
    payload = {
        "claims": len(claims),
        "report_path": str(path),
        "dry_run": args.dry_run,
        "summary": summarize(verdicts),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_report(verdicts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
