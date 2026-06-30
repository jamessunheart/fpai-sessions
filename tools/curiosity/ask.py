#!/usr/bin/env python3
"""Witness real state and ask one evidence-cited improvement question.

The Curiosity Engine is intentionally bounded: it reads local ground-truth
artifacts, generates at most one question, and routes it only through existing
queue surfaces. It does not deploy, merge, publish, send outreach, move money,
or invent evidence.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_QUESTION_LEDGER = REPO_ROOT / "core" / "BUILD" / "curiosity" / "questions.jsonl"
DEFAULT_OUTCOME_LEDGER = REPO_ROOT / "core" / "BUILD" / "curiosity" / "question_outcomes.jsonl"
DEFAULT_OPERATING_PRINCIPLE = REPO_ROOT / "core" / "STATE" / "OPERATING_PRINCIPLE.md"
DEFAULT_SEED = "What single change, verified by reality, would most increase the systems future rate of improvement?"
ACTIONABLE_KINDS = {"feature_outcome", "review_disagreement", "diff_risk", "conversion"}
RESERVED_TERMS = (
    "move money",
    "transfer",
    "withdraw",
    "send outreach",
    "publish",
    "deploy production",
    "touch secrets",
    "delete service",
    "archive service",
    "hire",
    "fire",
)


@dataclasses.dataclass(frozen=True)
class Evidence:
    kind: str
    source: str
    summary: str
    verdict: str = "unknown"
    spec_id: str = ""
    score: int = 0

    def citation(self) -> str:
        bits = [self.kind, self.source]
        if self.spec_id:
            bits.append(self.spec_id)
        return " | ".join(bits)


@dataclasses.dataclass(frozen=True)
class Question:
    question_id: str
    question: str
    route: str
    evidence: tuple[Evidence, ...]
    seed_prompt: str
    weakest_assumption: str

    def evidence_refs(self) -> list[str]:
        return [item.citation() for item in self.evidence]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_seed(path: Path = DEFAULT_OPERATING_PRINCIPLE) -> str:
    if not path.exists():
        return DEFAULT_SEED
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return DEFAULT_SEED
    first_question = re.search(r"([^.\n?]*\?)(?:\s|$)", text)
    return " ".join((first_question.group(1) if first_question else text.splitlines()[0]).split())


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with file_path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def collect_evidence(
    *,
    repo_root: Path = REPO_ROOT,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    transcript_paths: Iterable[Path] = (),
    true_narrator_paths: Iterable[Path] = (),
    conversion_ledgers: Iterable[Path] = (),
    max_items: int = 24,
) -> list[Evidence]:
    evidence: list[Evidence] = []
    evidence.extend(feature_outcome_evidence(ops_ledger))
    evidence.extend(review_disagreement_evidence(repo_root / "core" / "BUILD" / "reviews"))
    evidence.extend(diff_evidence(repo_root))
    for path in conversion_ledgers:
        evidence.extend(conversion_evidence(path))
    for path in transcript_paths:
        evidence.extend(text_file_evidence(path, kind="transcript", verdict="observed", score=20))
    for path in true_narrator_paths:
        evidence.extend(text_file_evidence(path, kind="true_narrator", verdict="observed", score=25))
    evidence.sort(key=lambda item: (item.score, item.source), reverse=True)
    return evidence[:max_items]


def feature_outcome_evidence(path: Path) -> list[Evidence]:
    scores = {"regressed": 120, "flat": 90, "unknown": 45, "improved": 15}
    out: list[Evidence] = []
    for line_no, row in enumerate(read_jsonl(path), start=1):
        if row.get("event") != "feature_outcome" and row.get("signal_type") != "feature_outcome":
            continue
        verdict = normalize(row.get("verdict") or row.get("outcome") or "unknown")
        spec_id = clean(row.get("spec_id") or row.get("spec") or "")
        metric = clean(row.get("metric_name") or row.get("metric") or "runtime quality")
        baseline = clean(row.get("baseline") or "unknown")
        observed = clean(row.get("observed") or "unknown")
        delta = clean(row.get("delta") or "")
        summary = f"{metric}: {baseline} -> {observed}"
        if delta:
            summary += f"; delta={delta}"
        out.append(Evidence("feature_outcome", f"{path}:{line_no}", summary, verdict, spec_id, scores.get(verdict, 45)))
    return out


def review_disagreement_evidence(reviews_dir: Path) -> list[Evidence]:
    if not reviews_dir.exists():
        return []
    out: list[Evidence] = []
    recent_reviews = sorted(reviews_dir.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True)[:20]
    for path in recent_reviews:
        text = path.read_text(encoding="utf-8", errors="replace")
        verdict = review_verdict(text)
        if verdict not in {"request_changes", "blocked"}:
            continue
        finding = first_finding(text) or first_substantive_line(text) or "review disagreed with the proposed build"
        score = 115 if verdict == "blocked" else 95
        out.append(Evidence("review_disagreement", rel(path), finding, verdict, spec_id=spec_from_name(path.name), score=score))
    return out


def diff_evidence(repo_root: Path) -> list[Evidence]:
    changed = git_lines(repo_root, ["diff", "--name-status", "feat/headless-build...HEAD"])
    if not changed:
        changed = git_lines(repo_root, ["status", "--short"])
    out: list[Evidence] = []
    protected = protected_prefixes(repo_root)
    for line in changed[:40]:
        parts = line.split()
        path = parts[-1] if parts else line
        risk = any(path == prefix or path.startswith(prefix) for prefix in protected)
        score = 110 if risk else 35
        verdict = "protected_path" if risk else "changed"
        out.append(Evidence("diff_risk", "git:" + path, line, verdict, score=score))
    return out


def conversion_evidence(path: Path) -> list[Evidence]:
    out: list[Evidence] = []
    for line_no, row in enumerate(read_jsonl(path), start=1):
        verdict = normalize(row.get("verdict") or row.get("outcome") or row.get("status") or "")
        if verdict not in {"regressed", "failed", "flat", "unknown", "missed"}:
            continue
        metric = clean(row.get("metric") or row.get("metric_name") or row.get("event") or "conversion")
        observed = clean(row.get("observed") or row.get("value") or row.get("detail") or verdict)
        out.append(Evidence("conversion", f"{path}:{line_no}", f"{metric}: {observed}", verdict, score=85))
    return out


def text_file_evidence(path: Path, *, kind: str, verdict: str, score: int) -> list[Evidence]:
    if not path.exists() or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    summary = first_substantive_line(text)
    if not summary:
        return []
    return [Evidence(kind, str(path), summary, verdict, score=score)]


def generate_question(evidence: list[Evidence], *, seed_prompt: str, outcome_ledger: Path = DEFAULT_OUTCOME_LEDGER) -> Question | None:
    real = [item for item in evidence if item.summary.strip()]
    if not real:
        return None
    weights = reinforcement_weights(outcome_ledger)
    ranked = sorted(real, key=lambda item: (item.score + weights.get(item.kind, 0), item.source), reverse=True)
    primary = ranked[0]
    supporting = tuple(ranked[: min(3, len(ranked))])
    assumption = weakest_assumption(primary)
    question_text = render_question(primary, supporting, seed_prompt=seed_prompt, assumption=assumption)
    question_id = "cq-" + hashlib.sha256((question_text + "|" + "|".join(e.source for e in supporting)).encode("utf-8")).hexdigest()[:12]
    route = "build" if primary.kind in ACTIONABLE_KINDS and not is_reserved(question_text) else "james"
    return Question(question_id, question_text, route, supporting, seed_prompt, assumption)


def weakest_assumption(evidence: Evidence) -> str:
    if evidence.kind == "feature_outcome":
        if evidence.verdict == "regressed":
            return "a merged build improves the system once activation completes"
        if evidence.verdict == "flat":
            return "shipping code is equivalent to increasing runtime improvement rate"
        return "runtime outcome evidence is already being converted into better next actions"
    if evidence.kind == "review_disagreement":
        return "the builder's self-assessment catches the same risks as independent review"
    if evidence.kind == "diff_risk":
        return "current file changes are inside the safe build lane"
    if evidence.kind == "conversion":
        return "attention is converting into the intended downstream result"
    if evidence.kind == "transcript":
        return "recent conversation state has been translated into the build queue"
    if evidence.kind == "true_narrator":
        return "observed reality and the system's self-story match"
    return "the current loop is improving at the fastest available rate"


def render_question(primary: Evidence, evidence: tuple[Evidence, ...], *, seed_prompt: str, assumption: str) -> str:
    citations = "; ".join(f"{item.citation()} -> {item.summary}" for item in evidence)
    return (
        f"{seed_prompt} Weakest assumption to test: {assumption}. "
        f"Evidence: {citations}. "
        "What single reversible build or James-gated answer would most directly test and improve that assumption next?"
    )


def route_question(
    question: Question,
    *,
    execute: bool,
    repo_root: Path = REPO_ROOT,
    queue_path: Path | None = None,
) -> dict[str, Any]:
    if question.route == "build":
        payload = {
            "question": question.question,
            "title": f"Curiosity Engine: {question.weakest_assumption}",
            "build_spec": json.dumps(
                {
                    "source": "tools/curiosity/ask.py",
                    "curiosity_question_id": question.question_id,
                    "question": question.question,
                    "evidence": question.evidence_refs(),
                    "required_gates": ["independent_ai_review", "protected_paths", "veto_reverse"],
                    "constraints": ["no deploy", "no push", "no merge", "no secrets", "no outreach", "no money movement"],
                },
                sort_keys=True,
            ),
            "proof_expected": "independent-AI-reviewed branch with tests; feature_outcome verdict tagged back to curiosity question",
        }
        if not execute:
            return {"status": "dry_run", "route": "build", "payload": payload}
        return seed_decision(payload, repo_root=repo_root)

    gate_payload = {
        "gate_id": question.question_id,
        "stream": "Game",
        "question": question.question,
        "verbs": ["build", "revise", "checkpoint"],
        "blocking": True,
        "urgent": False,
    }
    if not execute:
        return {"status": "dry_run", "route": "james", "payload": gate_payload}
    from tools.queue import build as human_edge_queue

    gate = human_edge_queue.add_gate(path=queue_path, **gate_payload)
    return {"status": "surfaced", "route": "james", "gate": gate}


def seed_decision(payload: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    brain = repo_root / "SERVICES" / "sunheart-brain"
    cmd = [sys.executable, "-m", "curator.decisions", "seed"]
    env = {**os.environ, "FPAI_REPO_ROOT": str(repo_root), "PYTHONPATH": str(brain)}
    result = subprocess.run(cmd, input=json.dumps(payload), capture_output=True, text=True, cwd=brain, env=env, timeout=20)
    if result.returncode != 0:
        return {"status": "error", "route": "build", "stderr": result.stderr.strip(), "stdout": result.stdout.strip()}
    try:
        body = json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        body = {"stdout": result.stdout.strip()}
    return {"status": "queued", "route": "build", "decision": body}


def append_question_row(path: Path, question: Question, route_result: dict[str, Any]) -> dict[str, Any]:
    row = {
        "ts": utc_now(),
        "event": "curiosity_question",
        "question_id": question.question_id,
        "question": question.question,
        "route": question.route,
        "status": route_result.get("status", "unknown"),
        "weakest_assumption": question.weakest_assumption,
        "seed_prompt": question.seed_prompt,
        "evidence": [
            {
                "kind": item.kind,
                "source": item.source,
                "summary": item.summary,
                "verdict": item.verdict,
                "spec_id": item.spec_id,
            }
            for item in question.evidence
        ],
        "route_result": route_result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def tag_question_outcome(
    *,
    question_id: str,
    triggered_spec_id: str,
    verdict: str,
    outcome_ledger: Path = DEFAULT_OUTCOME_LEDGER,
    evidence: Iterable[str] = (),
) -> dict[str, Any]:
    row = {
        "ts": utc_now(),
        "event": "curiosity_question_outcome",
        "question_id": question_id,
        "triggered_spec_id": triggered_spec_id,
        "verdict": normalize(verdict) or "unknown",
        "evidence": list(evidence),
    }
    outcome_ledger.parent.mkdir(parents=True, exist_ok=True)
    with outcome_ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def close_loop_from_feature_outcomes(
    *,
    question_ledger: Path = DEFAULT_QUESTION_LEDGER,
    outcome_ledger: Path = DEFAULT_OUTCOME_LEDGER,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
) -> list[dict[str, Any]]:
    questions = read_jsonl(question_ledger)
    existing = {(row.get("question_id"), row.get("triggered_spec_id")) for row in read_jsonl(outcome_ledger)}
    outcomes_by_spec = latest_feature_outcomes_by_spec(ops_ledger)
    tagged: list[dict[str, Any]] = []
    for question in questions:
        qid = str(question.get("question_id") or "")
        route_result = question.get("route_result") if isinstance(question.get("route_result"), dict) else {}
        triggered = str(question.get("triggered_spec_id") or route_result.get("triggered_spec_id") or "")
        if not qid or not triggered or (qid, triggered) in existing or triggered not in outcomes_by_spec:
            continue
        outcome = outcomes_by_spec[triggered]
        tagged.append(
            tag_question_outcome(
                question_id=qid,
                triggered_spec_id=triggered,
                verdict=str(outcome.get("verdict") or "unknown"),
                outcome_ledger=outcome_ledger,
                evidence=[str(outcome.get("source") or "")],
            )
        )
    return tagged


def latest_feature_outcomes_by_spec(path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for line_no, row in enumerate(read_jsonl(path), start=1):
        if row.get("event") != "feature_outcome" and row.get("signal_type") != "feature_outcome":
            continue
        spec_id = str(row.get("spec_id") or "")
        if not spec_id:
            continue
        latest[spec_id] = {**row, "source": f"{path}:{line_no}"}
    return latest


def reinforcement_weights(path: Path) -> dict[str, int]:
    weights: dict[str, int] = {}
    for row in read_jsonl(path):
        if row.get("event") != "curiosity_question_outcome":
            continue
        verdict = normalize(row.get("verdict") or "")
        if verdict == "improved":
            weights["feature_outcome"] = weights.get("feature_outcome", 0) + 15
        elif verdict == "regressed":
            weights["feature_outcome"] = weights.get("feature_outcome", 0) - 10
    return weights


def git_lines(repo_root: Path, args: list[str]) -> list[str]:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def protected_prefixes(repo_root: Path) -> list[str]:
    path = repo_root / "core" / "BUILD" / "PROTECTED_PATHS.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.strip().startswith("#")]


def is_reserved(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in RESERVED_TERMS)


def review_verdict(text: str) -> str:
    lowered = text.lower()
    if "blocked_protected" in lowered or "blocked" in lowered:
        return "blocked"
    if "request_changes" in lowered or "request changes" in lowered:
        return "request_changes"
    return "unknown"


def first_finding(text: str) -> str:
    match = re.search(r"(?ims)^## findings\s*\n(?P<body>.*?)(?=^## |\Z)", text)
    body = match.group("body") if match else text
    for line in body.splitlines():
        stripped = line.strip(" -\t")
        if stripped and stripped.lower() not in {"(none)", "none"}:
            return " ".join(stripped.split())[:360]
    return ""


def first_substantive_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip(" #-\t")
        if stripped and not stripped.startswith("---"):
            return " ".join(stripped.split())[:360]
    return ""


def spec_from_name(name: str) -> str:
    match = re.search(r"(SPEC_[A-Za-z0-9_.-]+)", name)
    return match.group(1).removesuffix(".md") if match else ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())[:360]


def normalize(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    aliases = {"failed": "regressed", "fail": "regressed", "worse": "regressed", "same": "flat", "passed": "improved", "pass": "improved"}
    return aliases.get(text, text)


def parse_paths(values: list[str]) -> list[Path]:
    out: list[Path] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item:
                out.append(Path(item))
    return out


def run_cycle(args: argparse.Namespace) -> int:
    seed = read_seed(args.operating_principle)
    if args.close_loop:
        tagged = close_loop_from_feature_outcomes(question_ledger=args.question_ledger, outcome_ledger=args.outcome_ledger, ops_ledger=args.ops_ledger)
        print(json.dumps({"ok": True, "tagged": tagged}, indent=2, sort_keys=True))
        return 0
    if args.tag_outcome:
        row = tag_question_outcome(
            question_id=args.question_id,
            triggered_spec_id=args.triggered_spec_id,
            verdict=args.verdict,
            outcome_ledger=args.outcome_ledger,
            evidence=args.evidence,
        )
        print(json.dumps({"ok": True, "row": row}, indent=2, sort_keys=True))
        return 0
    evidence = collect_evidence(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        transcript_paths=parse_paths(args.transcript),
        true_narrator_paths=parse_paths(args.true_narrator),
        conversion_ledgers=parse_paths(args.conversion_ledger),
    )
    question = generate_question(evidence, seed_prompt=seed, outcome_ledger=args.outcome_ledger)
    if question is None:
        print(json.dumps({"ok": True, "question": None, "reason": "no real evidence available"}, sort_keys=True))
        return 0
    route_result = route_question(question, execute=args.execute, repo_root=args.repo_root, queue_path=args.queue_path)
    row = append_question_row(args.question_ledger, question, route_result)
    print(json.dumps({"ok": True, "question": row}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Witness real state and ask at most one evidence-cited question.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--question-ledger", type=Path, default=DEFAULT_QUESTION_LEDGER)
    parser.add_argument("--outcome-ledger", type=Path, default=DEFAULT_OUTCOME_LEDGER)
    parser.add_argument("--operating-principle", type=Path, default=DEFAULT_OPERATING_PRINCIPLE)
    parser.add_argument("--transcript", action="append", default=[], help="optional transcript file path; repeatable or comma-separated")
    parser.add_argument("--true-narrator", action="append", default=[], help="optional true-narrator file path; repeatable or comma-separated")
    parser.add_argument("--conversion-ledger", action="append", default=[], help="optional conversion JSONL path; repeatable or comma-separated")
    parser.add_argument("--queue-path", type=Path, help="optional HUMAN_EDGE_QUEUE.json path for James-gated questions")
    parser.add_argument("--execute", action="store_true", help="write to the live queue path; default is dry-run plus ledger row")
    parser.add_argument("--close-loop", action="store_true", help="tag queued questions with available feature_outcome rows")
    parser.add_argument("--tag-outcome", action="store_true", help="append an explicit curiosity_question_outcome row")
    parser.add_argument("--question-id", default="")
    parser.add_argument("--triggered-spec-id", default="")
    parser.add_argument("--verdict", default="unknown")
    parser.add_argument("--evidence", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.tag_outcome and (not args.question_id or not args.triggered_spec_id):
        parser.error("--tag-outcome requires --question-id and --triggered-spec-id")
    return run_cycle(args)


if __name__ == "__main__":
    raise SystemExit(main())
