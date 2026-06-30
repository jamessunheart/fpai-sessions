#!/usr/bin/env python3
"""Capture session-level feedback signals into an advisory preference seed.

This is the d023 continuous-learning L1 artifact. It reads repo-local build
feedback surfaces and optional explicit feedback JSONL, emits deterministic
JSONL rows, and never trains, deploys, routes, spends, or grants authority.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "tools" / "learn" / "runs" / "session_feedback_seed.jsonl"
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
DEFAULT_REVIEWS = REPO_ROOT / "core" / "BUILD" / "reviews"
DEFAULT_FEEDBACK_GLOB = "core/BUILD/feedback*.jsonl"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
SCHEMA = "session-feedback-seed.v1"

POSITIVE_STATUSES = {"merged", "approved", "approve"}
NEGATIVE_STATUSES = {"rejected", "failed", "regressed", "blocked", "vetoed", "request_changes", "changes_requested"}
NEUTRAL_STATUSES = {"building", "done", "pending", "queued", "awaiting_review", "awaiting merge", "awaiting diff review"}


@dataclasses.dataclass(frozen=True)
class SessionFeedback:
    """One structured learning signal from a build/chat session."""

    signal_type: str
    session_id: str
    source: str
    captured_at: str
    outcome: str
    score: float
    prompt: str
    chosen: str
    rejected: str
    metadata: dict[str, Any]

    @property
    def row_id(self) -> str:
        digest = hashlib.sha256(
            "\n".join(
                [
                    SCHEMA,
                    self.signal_type,
                    self.session_id,
                    self.source,
                    self.outcome,
                    self.prompt,
                    self.chosen,
                    self.rejected,
                ]
            ).encode("utf-8")
        ).hexdigest()
        return f"sf-{digest[:16]}"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "id": self.row_id,
            "captured_at": self.captured_at,
            "session_id": self.session_id,
            "signal_type": self.signal_type,
            "source": self.source,
            "outcome": self.outcome,
            "score": self.score,
            "prompt": self.prompt,
            "preference": {
                "chosen": self.chosen,
                "rejected": self.rejected,
            },
            "metadata": self.metadata,
        }


def collect_session_feedback(
    root: Path | str = REPO_ROOT,
    *,
    registry: Path | None = None,
    reviews_dir: Path | None = None,
    feedback_glob: str = DEFAULT_FEEDBACK_GLOB,
    ops_ledger: Path | None = None,
    captured_at: str | None = None,
) -> list[dict[str, Any]]:
    """Collect deterministic session feedback rows from repo-local surfaces."""
    repo = Path(root)
    stamp = captured_at or _now()
    signals: list[SessionFeedback] = []
    signals.extend(_from_registry(registry or repo / "core" / "BUILD" / "REGISTRY.json", captured_at=stamp))
    signals.extend(_from_reviews(reviews_dir or repo / "core" / "BUILD" / "reviews", captured_at=stamp))
    signals.extend(_from_explicit_feedback(repo, feedback_glob=feedback_glob, captured_at=stamp))
    if ops_ledger is not None:
        signals.extend(_from_feature_outcomes(ops_ledger, captured_at=stamp))

    unique: dict[str, SessionFeedback] = {}
    for signal in signals:
        if signal.prompt and (signal.chosen or signal.rejected):
            unique.setdefault(signal.row_id, signal)
    return [item.to_json() for item in sorted(unique.values(), key=lambda row: row.row_id)]


def collect_feature_outcome_feedback(path: Path | str, *, captured_at: str | None = None) -> list[dict[str, Any]]:
    """Collect feature_outcome rows from the ops ledger as feedback rows."""
    stamp = captured_at or _now()
    return [item.to_json() for item in _from_feature_outcomes(Path(path), captured_at=stamp)]


def write_jsonl(rows: Iterable[dict[str, Any]], output: Path | str = DEFAULT_OUTPUT) -> Path:
    """Write rows to JSONL and return the output path."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def append_jsonl(rows: Iterable[dict[str, Any]], output: Path | str = DEFAULT_OUTPUT) -> int:
    """Append rows, deduping by row id. Return the number written."""
    path = Path(output)
    existing = _existing_ids(path)
    pending = [row for row in rows if row.get("id") not in existing]
    if not pending:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in pending:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(pending)


def _from_registry(path: Path, *, captured_at: str) -> list[SessionFeedback]:
    data = _read_json(path)
    if not isinstance(data, dict):
        return []
    rows = data.get("active_builds")
    if not isinstance(rows, list):
        return []

    signals: list[SessionFeedback] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        status = _normalize_status(item.get("status"))
        if status in NEUTRAL_STATUSES or not status:
            continue
        score = _score_for_status(status)
        session_id = _clean(item.get("id") or item.get("slug") or item.get("branch") or path.stem)
        branch = _clean(item.get("branch"))
        spec = _clean(item.get("spec"))
        notes = _clean(item.get("notes"))
        prompt = f"Build session {session_id}: {spec or branch}"
        if score >= 0:
            chosen = notes or f"{branch or session_id} reached {status}."
            rejected = "Leaving the session unmerged or unresolved."
        else:
            chosen = "Stop, revise, or route the session for repair before treating it as learned success."
            rejected = notes or f"{branch or session_id} reached {status}."
        signals.append(
            SessionFeedback(
                signal_type="merge_outcome" if status == "merged" else "build_outcome",
                session_id=session_id,
                source=str(path),
                captured_at=captured_at,
                outcome=status,
                score=score,
                prompt=prompt,
                chosen=chosen,
                rejected=rejected,
                metadata={
                    "branch": branch,
                    "base_branch": _clean(item.get("base_branch")),
                    "tests_passed": item.get("tests_passed"),
                    "registry_status": status,
                },
            )
        )
    return signals


def _from_reviews(path: Path, *, captured_at: str) -> list[SessionFeedback]:
    if not path.exists():
        return []
    signals: list[SessionFeedback] = []
    for review in sorted(path.glob("*.md")):
        text = review.read_text(encoding="utf-8", errors="ignore")
        verdict = _extract_review_verdict(text)
        if not verdict:
            continue
        status = _normalize_status(verdict)
        score = _score_for_status(status)
        title = _first_heading(text) or review.stem
        summary = _extract_label(text, "Summary") or title
        findings = _extract_findings(text)
        if score >= 0:
            chosen = summary
            rejected = "Ignoring independent review findings before merge."
            signal_type = "review_outcome"
        else:
            chosen = "Respect the independent review veto and repair the branch before merge."
            rejected = summary
            signal_type = "veto"
        signals.append(
            SessionFeedback(
                signal_type=signal_type,
                session_id=review.stem,
                source=str(review),
                captured_at=captured_at,
                outcome=status,
                score=score,
                prompt=f"Independent AI review for {title}",
                chosen=chosen,
                rejected=rejected,
                metadata={
                    "verdict": verdict,
                    "findings": findings,
                },
            )
        )
    return signals


def _from_explicit_feedback(repo: Path, *, feedback_glob: str, captured_at: str) -> list[SessionFeedback]:
    signals: list[SessionFeedback] = []
    for path in sorted(repo.glob(feedback_glob)):
        for line_no, item in enumerate(_read_jsonl(path), start=1):
            signal = _explicit_signal_from_mapping(path, line_no, item, captured_at=captured_at)
            if signal:
                signals.append(signal)
    return signals


def _from_feature_outcomes(path: Path, *, captured_at: str) -> list[SessionFeedback]:
    signals: list[SessionFeedback] = []
    for line_no, row in enumerate(_read_jsonl(path), start=1):
        if row.get("event") != "feature_outcome" and row.get("signal_type") != "feature_outcome":
            continue
        spec_id = _clean(row.get("spec_id") or row.get("spec") or row.get("id") or f"{path.stem}:{line_no}")
        metric = _clean(row.get("metric_name") or row.get("metric") or "runtime_quality")
        baseline = _clean(row.get("baseline"))
        observed = _clean(row.get("observed"))
        delta = _clean(row.get("delta"))
        verdict = _normalize_feature_verdict(row.get("verdict") or row.get("outcome"))
        score = _score_for_feature_verdict(verdict)
        evidence = row.get("evidence")
        if isinstance(evidence, list):
            evidence_text = "; ".join(_clean(item) for item in evidence if _clean(item))
        else:
            evidence_text = _clean(evidence)
        if verdict == "improved":
            chosen = f"Reuse the build pattern because {metric} improved: {observed or delta}."
            rejected = f"Ignore runtime outcome evidence for {spec_id}."
        elif verdict == "regressed":
            chosen = f"Treat this as a caution before reusing the pattern: {delta or observed}."
            rejected = f"Repeat the same pattern from {spec_id} without checking runtime evidence."
        elif verdict == "flat":
            chosen = f"Keep the pattern neutral until a stronger runtime delta appears: {delta or observed}."
            rejected = f"Overclaim improvement from a flat runtime result."
        else:
            chosen = "Keep this feature outcome out of strong principles until runtime evidence is clearer."
            rejected = f"Treat unknown runtime quality for {spec_id} as a proven success."
        signals.append(
            SessionFeedback(
                signal_type="feature_outcome",
                session_id=spec_id,
                source=f"{path}:{line_no}",
                captured_at=_clean(row.get("ts") or row.get("captured_at")) or captured_at,
                outcome=verdict,
                score=score,
                prompt=f"Runtime outcome for {spec_id}: {metric}",
                chosen=chosen,
                rejected=rejected,
                metadata={
                    "metric_name": metric,
                    "baseline": baseline,
                    "observed": observed,
                    "delta": delta,
                    "verdict": verdict,
                    "evidence": evidence_text,
                },
            )
        )
    return signals


def _explicit_signal_from_mapping(
    path: Path,
    line_no: int,
    item: dict[str, Any],
    *,
    captured_at: str,
) -> SessionFeedback | None:
    signal_type = _clean(item.get("signal_type") or item.get("type") or item.get("event"))
    rating = item.get("rating")
    veto = item.get("veto") or item.get("vetoed")
    if not signal_type:
        if rating is not None:
            signal_type = "conversation_rating"
        elif veto:
            signal_type = "veto"
    if signal_type not in {"conversation_rating", "veto", "merge_outcome", "review_outcome", "feature_outcome"}:
        return None

    session_id = _clean(item.get("session_id") or item.get("conversation_id") or item.get("id") or f"{path.stem}:{line_no}")
    prompt = _clean(item.get("prompt") or item.get("context") or item.get("summary") or f"Session feedback {session_id}")
    comment = _clean(item.get("comment") or item.get("reason") or item.get("feedback") or item.get("notes"))
    chosen = _clean(item.get("chosen") or item.get("preferred"))
    rejected = _clean(item.get("rejected") or item.get("bad") or item.get("vetoed_action"))

    outcome = _clean(item.get("outcome") or item.get("verdict"))
    score = 0.0
    if signal_type == "conversation_rating":
        normalized = _normalize_rating(rating, scale=item.get("rating_scale") or item.get("scale"))
        if normalized is None:
            return None
        score = normalized
        outcome = outcome or ("positive" if score > 0 else "negative" if score < 0 else "neutral")
        chosen = chosen or (comment if score >= 0 else "Adjust future responses according to James's rating feedback.")
        rejected = rejected or ("Ignoring James's explicit conversation rating." if score >= 0 else comment)
    elif signal_type == "veto":
        score = -1.0
        outcome = _normalize_status(outcome or "vetoed")
        chosen = chosen or "Treat James's veto as a hard preference boundary for the next loop."
        rejected = rejected or comment or "The vetoed action or behavior."
    elif signal_type == "feature_outcome":
        outcome = _normalize_feature_verdict(outcome or item.get("verdict"))
        score = _score_for_feature_verdict(outcome)
        chosen = chosen or comment or f"Runtime outcome was {outcome}."
        rejected = rejected or "Ignoring runtime-quality evidence."
    else:
        outcome = _normalize_status(outcome or "done")
        score = _score_for_status(outcome)
        chosen = chosen or comment or f"Session reached {outcome}."
        rejected = rejected or "Treating the session as unreviewed."

    return SessionFeedback(
        signal_type=signal_type,
        session_id=session_id,
        source=f"{path}:{line_no}",
        captured_at=_clean(item.get("captured_at") or item.get("created_at")) or captured_at,
        outcome=outcome,
        score=score,
        prompt=prompt,
        chosen=chosen,
        rejected=rejected,
        metadata={
            "raw_rating": rating,
            "comment": comment,
        },
    )


def _normalize_rating(value: Any, *, scale: Any = None) -> float | None:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    scale_name = _clean(scale).lower()
    if scale_name in {"1-5", "5", "likert", "likert_5", "stars"} and 1 <= rating <= 5:
        return round((rating - 3) / 2, 3)
    if scale_name in {"-1..1", "-1_to_1", "signed", "normalized"} and -1 <= rating <= 1:
        return round(rating, 3)
    if -1 <= rating <= 1:
        return round(rating, 3)
    if 1 <= rating <= 5:
        return round((rating - 3) / 2, 3)
    if 0 <= rating <= 10:
        return round((rating - 5) / 5, 3)
    return None


def _score_for_status(status: str) -> float:
    if status in POSITIVE_STATUSES:
        return 1.0
    if status in NEGATIVE_STATUSES:
        return -1.0
    return 0.0


def _normalize_feature_verdict(value: Any) -> str:
    text = _clean(value).lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "better": "improved",
        "pass": "improved",
        "passed": "improved",
        "success": "improved",
        "same": "flat",
        "neutral": "flat",
        "failed": "regressed",
        "fail": "regressed",
        "worse": "regressed",
    }
    verdict = aliases.get(text, text)
    return verdict if verdict in {"improved", "flat", "regressed", "unknown"} else "unknown"


def _score_for_feature_verdict(verdict: str) -> float:
    if verdict == "improved":
        return 1.0
    if verdict == "regressed":
        return -1.0
    return 0.0


def _normalize_status(value: Any) -> str:
    text = _clean(value).lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "approved": "approve",
        "pass": "approve",
        "passed": "approve",
        "request_change": "changes_requested",
        "request_changes": "changes_requested",
        "requested_changes": "changes_requested",
        "needs_work": "changes_requested",
        "requestchanges": "changes_requested",
    }
    return aliases.get(text, text)


def _extract_review_verdict(text: str) -> str | None:
    match = re.search(r"\*\*Verdict:\*\*\s*([A-Za-z_ -]+)", text)
    if match:
        return match.group(1).split("·", 1)[0].strip()
    match = re.search(r"^Verdict:\s*([A-Za-z_ -]+)", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _extract_label(text: str, label: str) -> str | None:
    match = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", text)
    return _clean(match.group(1)) if match else None


def _extract_findings(text: str) -> list[str]:
    findings: list[str] = []
    in_findings = False
    for line in text.splitlines():
        if line.strip().lower() == "## findings":
            in_findings = True
            continue
        if in_findings and line.startswith("## "):
            break
        if in_findings and line.lstrip().startswith("-"):
            findings.append(_clean(line.lstrip("- ")))
    return findings[:12]


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return _clean(line.lstrip("# "))
    return None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        handle = path.open(encoding="utf-8")
    except OSError:
        return rows
    with handle:
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


def _existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {str(row["id"]) for row in _read_jsonl(path) if row.get("id")}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture session-level feedback into a structured JSONL seed.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--reviews-dir", type=Path, default=None)
    parser.add_argument("--feedback-glob", default=DEFAULT_FEEDBACK_GLOB)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--append", action="store_true", help="append new rows instead of replacing output")
    parser.add_argument("--dry-run", action="store_true", help="print summary only; do not write output")
    args = parser.parse_args(argv)

    try:
        rows = collect_session_feedback(
            args.root,
            registry=args.registry,
            reviews_dir=args.reviews_dir,
            feedback_glob=args.feedback_glob,
            ops_ledger=args.ops_ledger,
        )
        wrote = 0
        if not args.dry_run:
            wrote = append_jsonl(rows, args.output) if args.append else len(rows)
            if not args.append:
                write_jsonl(rows, args.output)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows),
                "wrote": wrote,
                "output": str(args.output),
                "dry_run": args.dry_run,
                "append": args.append,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
