#!/usr/bin/env python3
"""Quality + value curation for autonomous product candidates.

This does not stop the system from building. It gives James a portfolio view:
what was built, whether it works, who would pay, and whether the next move is
keep, develop, or kill. Launch/funding/public voice remain Reserved.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW_PATH = Path(
    os.environ.get("FPAI_PRODUCT_PORTFOLIO_REVIEW", "/opt/fpai-build/product_portfolio_review.md")
)
LOW_QUALITY_THRESHOLD = 60

TEST_OK = re.compile(r"\b(OK|passed|PASS|0 failed|git diff --check|py_compile|bash -n|smoke)\b", re.IGNORECASE)
TEST_BAD = re.compile(r"\b(fail(?:ed|ure)?|error|traceback|not run|untested)\b", re.IGNORECASE)
SCAFFOLD_ONLY = re.compile(r"\b(scaffold|placeholder|stub|skeleton|not implemented|todo)\b", re.IGNORECASE)
FUNCTIONAL = re.compile(
    r"\b(endpoint|fixture|payload|delivery|writes?|persists?|scores?|captures?|renders?|"
    r"activation|smoke|expected|regression|lead|appointment|assessment|CLI)\b",
    re.IGNORECASE,
)
VALUE_ALIGNED = re.compile(
    r"\b(allocation|bottleneck|assessment|funnel|revenue|cash|buyer|pay|offer|"
    r"business|operator|founder|recurring|implementation|diagnostic)\b",
    re.IGNORECASE,
)


def assess_candidate(
    *,
    repo_root: Path = REPO_ROOT,
    opportunity: dict[str, Any] | None = None,
    spec_id: str = "",
    branch: str = "",
    result_path: Path | None = None,
    test_report_path: Path | None = None,
) -> dict[str, Any]:
    opportunity = opportunity or {}
    result_path = result_path or find_result_for_candidate(repo_root, spec_id=spec_id, opportunity=opportunity)
    test_report_path = test_report_path or find_test_report(repo_root, spec_id=spec_id)
    result_text = read_text(result_path) if result_path else ""
    test_report = read_test_report(test_report_path)
    title = str(opportunity.get("title") or spec_id or (result_path.stem if result_path else "Untitled candidate"))
    quality = quality_score(result_text=result_text, result_path=result_path, test_report=test_report)
    value = value_score(opportunity=opportunity, result_text=result_text)
    recommendation = recommend(quality["score"], value["score"])
    return {
        "schema": "fpai_product_candidate_assessment_v1",
        "id": str(opportunity.get("id") or spec_id or ""),
        "title": title,
        "spec_id": spec_id,
        "branch": branch,
        "result_path": str(result_path) if result_path else "",
        "test_report_path": str(test_report_path) if test_report_path else "",
        "test_status": test_report.get("status", "") if test_report else "",
        "test_counts": test_report.get("counts", {}) if test_report else {},
        "quality_score": quality["score"],
        "quality_take": quality["take"],
        "quality_flags": quality["flags"],
        "value_score": value["score"],
        "value_take": value["take"],
        "who_would_pay": value["who_would_pay"],
        "recommendation": recommendation,
        "low_quality": quality["score"] < LOW_QUALITY_THRESHOLD,
        "reserved_boundary": "Building candidates is reversible; LAUNCH/fund/public voice/money remain James-reserved.",
    }


def assess_portfolio(
    *,
    repo_root: Path = REPO_ROOT,
    opportunities: Iterable[dict[str, Any]],
    limit: int = 5,
) -> dict[str, Any]:
    candidates = [assess_candidate(repo_root=repo_root, opportunity=row) for row in list(opportunities)[:limit]]
    return {
        "schema": "fpai_product_portfolio_review_v1",
        "count": len(candidates),
        "low_quality_count": sum(1 for row in candidates if row["low_quality"]),
        "reserved_boundary": "James curates value. The system may build reversible candidates; it may not launch/fund/use James voice.",
        "candidates": candidates,
    }


def quality_score(*, result_text: str, result_path: Path | None, test_report: dict[str, Any] | None = None) -> dict[str, Any]:
    flags: list[str] = []
    score = 20
    lower = result_text.lower()
    if result_path and result_path.exists():
        score += 10
    else:
        flags.append("no build result artifact found")
    if "tests:" in lower and TEST_OK.search(result_text):
        score += 30
    else:
        flags.append("tests not proven in result artifact")
    if re.search(r"\b(py_compile|lint|bash -n|git diff --check)\b", result_text, re.IGNORECASE):
        score += 12
    else:
        flags.append("lint/compile/shell hygiene not visible")
    if FUNCTIONAL.search(result_text):
        score += 20
    else:
        flags.append("real functionality not visible beyond scaffolding")
    if re.search(r"\bfixture|expected|regression|smoke\b", result_text, re.IGNORECASE):
        score += 10
    else:
        flags.append("no fixture/regression/smoke proof visible")
    if TEST_BAD.search(result_text):
        score -= 25
        flags.append("failure or untested language present")
    if SCAFFOLD_ONLY.search(result_text) and not FUNCTIONAL.search(result_text):
        score -= 20
        flags.append("scaffolding risk")
    if test_report:
        status = str(test_report.get("status") or "").lower()
        counts = test_report.get("counts") or {}
        if status == "passed":
            score += 15
        elif status == "skipped":
            flags.append("pytest gate skipped; no scoped tests selected")
        else:
            score -= 45
            failed = int(counts.get("failed") or 0)
            errors = int(counts.get("errors") or 0)
            flags.append(f"pytest gate {status or 'failed'}: failed={failed} errors={errors}")
    score = clamp(score)
    if score >= 85:
        take = "works on the available proof; quality looks mergeable pending normal review"
    elif score >= LOW_QUALITY_THRESHOLD:
        take = "partly proven; develop or review before relying on it"
    else:
        take = "weak proof; flag instead of silently merging"
    return {"score": score, "take": take, "flags": flags}


def value_score(*, opportunity: dict[str, Any], result_text: str) -> dict[str, Any]:
    axes = opportunity.get("axes") or {}
    questions = opportunity.get("questions") or {}
    title = str(opportunity.get("title") or "")
    who = str(questions.get("who_pays") or opportunity.get("who_pays") or "").strip()
    text = " ".join([title, who, str(questions.get("problem") or ""), result_text])
    allocation = number(opportunity.get("allocation_score"))
    if allocation is None:
        allocation = allocation_from_axes(axes)
    cash = number(opportunity.get("cash_proximity_score"))
    score = 30
    if allocation is not None:
        score += min(30, max(0, allocation * 1.2))
    if cash is not None:
        score += min(15, max(0, cash))
    if who:
        score += 15
    if VALUE_ALIGNED.search(text):
        score += 10
    if "james_reserved" in json.dumps(opportunity.get("topple") or {}).lower():
        score -= 8
    score = clamp(score)
    if not who:
        who = "buyer not clearly named"
    if score >= 80:
        take = "valuable/aligned candidate; likely worth keeping or developing"
    elif score >= 55:
        take = "plausible value, but buyer/proof/path needs sharpening"
    else:
        take = "value unclear relative to the offer and Allocation-Intelligence thesis"
    return {"score": score, "take": take, "who_would_pay": who}


def recommend(quality: int, value: int) -> str:
    if quality < LOW_QUALITY_THRESHOLD:
        return "kill" if value < 70 else "develop"
    if value < 50:
        return "kill"
    if quality >= 80 and value >= 75:
        return "keep"
    return "develop"


def render_review(review: dict[str, Any], *, html_mode: bool = False) -> str:
    if html_mode:
        return render_review(review, html_mode=False)
    lines = [
        "PORTFOLIO REVIEW - autonomous product candidates",
        review.get("reserved_boundary", ""),
        f"candidates: {review.get('count', 0)} - low-quality flagged: {review.get('low_quality_count', 0)}",
        "",
    ]
    for idx, row in enumerate(review.get("candidates", []), 1):
        flags = "; ".join(row.get("quality_flags") or []) or "none"
        lines.extend(
            [
                f"{idx}. {row.get('title') or row.get('id')}",
                f"   QUALITY {row.get('quality_score')}/100 - {row.get('quality_take')}",
                f"   VALUE {row.get('value_score')}/100 - {row.get('value_take')}",
                f"   Who would pay: {row.get('who_would_pay')}",
                f"   Rec: {str(row.get('recommendation') or '').upper()}",
                f"   Flags: {flags}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_review(path: Path, review: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_review(review), encoding="utf-8")


def notify_review(repo_root: Path, review: dict[str, Any], sender: Any | None = None) -> bool:
    message = render_review(review)[:3500]
    if sender:
        return bool(sender(message))
    script = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return False
    try:
        return subprocess.run(["bash", str(script), message], cwd=repo_root, timeout=20).returncode == 0
    except Exception:
        return False


def find_result_for_candidate(repo_root: Path, *, spec_id: str = "", opportunity: dict[str, Any] | None = None) -> Path | None:
    results = repo_root / "core" / "BUILD" / "results"
    if spec_id:
        direct = results / f"{spec_id}.result.md"
        if direct.exists():
            return direct
    if not results.exists():
        return None
    needles = [str((opportunity or {}).get("id") or "").lower(), str((opportunity or {}).get("title") or "").lower()]
    needles = [item for item in needles if item]
    for path in sorted(results.glob("*.result.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:80]:
        text = read_text(path).lower()
        if any(needle in text for needle in needles):
            return path
    return None


def find_test_report(repo_root: Path, *, spec_id: str = "") -> Path | None:
    if not spec_id:
        return None
    path = repo_root / "core" / "BUILD" / "reports" / f"{spec_id}.test_gate.json"
    return path if path.exists() else None


def read_test_report(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path | None) -> str:
    if not path:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def allocation_from_axes(axes: dict[str, Any]) -> float | None:
    values = {key: number(value) for key, value in axes.items()}
    required = ("pain", "market", "compounding", "difficulty", "time_to_revenue", "time_to_first_dollar", "path_to_recurring")
    if any(values.get(key) is None for key in required):
        return None
    base = values["pain"] * values["market"] * values["compounding"] / max(1.0, values["difficulty"] + values["time_to_revenue"])
    return base + (10.0 - values["time_to_first_dollar"]) + values["path_to_recurring"] - values["difficulty"] * 0.7 - values["time_to_revenue"] * 0.5


def number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float) -> int:
    return int(round(max(0, min(100, value))))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--spec-id", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--test-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_REVIEW_PATH)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-low-quality", action="store_true")
    args = parser.parse_args(argv)

    assessment = assess_candidate(
        repo_root=args.repo_root,
        spec_id=args.spec_id,
        branch=args.branch,
        result_path=args.result,
        test_report_path=args.test_report,
    )
    if args.json:
        print(json.dumps(assessment, indent=2, sort_keys=True))
    else:
        review = {
            "schema": "fpai_product_portfolio_review_v1",
            "count": 1,
            "low_quality_count": 1 if assessment["low_quality"] else 0,
            "reserved_boundary": assessment["reserved_boundary"],
            "candidates": [assessment],
        }
        write_review(args.output, review)
        print(render_review(review), end="")
    if args.fail_on_low_quality and assessment["low_quality"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
