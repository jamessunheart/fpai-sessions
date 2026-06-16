#!/usr/bin/env python3
"""Weekly spec-vs-diff checker for recently built decisions."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
CLAUDE_TIMEOUT_SECONDS = float(os.environ.get("SPEC_CHECKER_CLAUDE_TIMEOUT_SECONDS", "300"))


@dataclass
class SpecCheckResult:
    decision_id: str
    matches: bool
    gaps: list[str]
    risk: str
    raw: str = ""


def append_ops_row(ops_ledger: Path, row: dict[str, Any]) -> None:
    ops_ledger.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "spec_checker",
        "event": "spec_gap" if row.get("gaps") else "spec_check",
        "detail": "; ".join(row.get("gaps") or []) or "spec check matched",
        "cost": "$0",
        "artifact": "tools/test/spec_checker.py",
        "next": "review high-risk spec compliance gap" if row.get("risk") == "high" else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    data.update(row)
    with ops_ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, sort_keys=True) + "\n")


def parse_claude_json(text: str, *, decision_id: str) -> SpecCheckResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    data = json.loads(cleaned)
    gaps = [str(item) for item in data.get("gaps", [])]
    risk = str(data.get("risk", "low")).lower()
    if risk not in {"low", "med", "high"}:
        risk = "med"
    return SpecCheckResult(
        decision_id=decision_id,
        matches=bool(data.get("matches", False)),
        gaps=gaps,
        risk=risk,
        raw=text,
    )


def run_claude_check(
    decision_id: str,
    spec_text: str,
    diff_text: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> SpecCheckResult:
    prompt = (
        "Does this diff implement what this spec required? "
        "List what is missing or diverged. "
        "Return only JSON: {\"matches\": bool, \"gaps\": [str], \"risk\": \"low|med|high\"}\n\n"
        f"SPEC:\n{spec_text}\n\nDIFF:\n{diff_text}"
    )
    completed = runner(
        ["claude", "-p", "--effort", "high", prompt],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=CLAUDE_TIMEOUT_SECONDS,
    )
    return parse_claude_json(completed.stdout, decision_id=decision_id)


def git_diff_for_branch(repo_root: Path, branch: str, base: str = "feat/headless-build") -> str:
    merge_base = subprocess.check_output(
        ["git", "-C", str(repo_root), "merge-base", base, branch],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "diff", merge_base, branch],
        text=True,
        stderr=subprocess.DEVNULL,
    )


def normalize_decision_id(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("SPEC_"):
        text = text[5:]
    if text.startswith("d"):
        return text[:4]
    if text.isdigit():
        return f"d{int(text):03d}"
    return text


def persisted_diff_path(repo_root: Path, decision_id: str) -> Path:
    return repo_root / "core" / "BUILD" / "diffs" / f"{decision_id}.diff"


def load_original_build_spec(decision_id: str) -> str | None:
    try:
        import psycopg
    except ImportError:
        return None
    dsn = os.environ.get(
        "BRAIN_INDEX_DB_URL",
        "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
    )
    did = normalize_decision_id(decision_id)
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT build_spec
                      FROM brain_index.decisions
                     WHERE id::text = %s
                        OR id::text = %s
                     ORDER BY created_at DESC
                     LIMIT 1
                    """,
                    (decision_id, did),
                )
                row = cur.fetchone()
    except Exception:
        return None
    if not row or not row[0]:
        return None
    return str(row[0])


def send_alert(text: str) -> bool:
    if os.environ.get("SMOKE_TEST_SILENT") == "1":
        return False
    script = REPO_ROOT / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return False
    return subprocess.run([str(script), text], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def check_one(
    decision_id: str,
    spec_text: str,
    diff_text: str,
    *,
    ops_ledger: Path,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    alert: Callable[[str], bool] = send_alert,
) -> SpecCheckResult:
    result = run_claude_check(decision_id, spec_text, diff_text, runner=runner)
    append_ops_row(
        ops_ledger,
        {
            "decision_id": result.decision_id,
            "matches": result.matches,
            "gaps": result.gaps,
            "risk": result.risk,
        },
    )
    if result.risk == "high":
        alert(f"SPEC COMPLIANCE HIGH RISK {decision_id}: {'; '.join(result.gaps) or 'unspecified gap'}")
    return result


def registry_recent_checks(repo_root: Path, limit: int) -> list[tuple[str, Path, str]]:
    registry = repo_root / "core" / "BUILD" / "REGISTRY.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[tuple[str, Path, str]] = []
    for row in data.get("active_builds", []):
        if row.get("status") not in {"done", "merged"}:
            continue
        decision_id = str(row.get("id") or row.get("slug") or "")
        branch = str(row.get("branch") or "")
        spec_path = Path(str(row.get("spec") or ""))
        if not spec_path.is_absolute():
            spec_path = repo_root / spec_path
        if decision_id and branch and spec_path.exists():
            out.append((decision_id, spec_path, branch))
        if len(out) >= limit:
            break
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run weekly spec compliance check")
    parser.add_argument("--decision-id", help="decision id, e.g. d049")
    parser.add_argument("--spec-file", type=Path)
    parser.add_argument("--branch", help="git branch/ref to diff")
    parser.add_argument("--diff-file", type=Path, help="test helper: read diff text from file")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base", default="feat/headless-build")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--recent", action="store_true", help="check recent done/merged registry entries with available branches")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.recent:
        results: list[SpecCheckResult] = []
        for decision_id, spec_file, branch in registry_recent_checks(args.repo_root, args.limit):
            diff_artifact = persisted_diff_path(args.repo_root, decision_id)
            if diff_artifact.exists():
                diff_text = diff_artifact.read_text(encoding="utf-8", errors="replace")
            else:
                normalized_diff_artifact = persisted_diff_path(args.repo_root, normalize_decision_id(decision_id))
                if normalized_diff_artifact.exists():
                    diff_text = normalized_diff_artifact.read_text(encoding="utf-8", errors="replace")
                else:
                    try:
                        diff_text = git_diff_for_branch(args.repo_root, branch, args.base)
                    except Exception as exc:
                        append_ops_row(args.ops_ledger, {
                            "decision_id": decision_id,
                            "matches": False,
                            "gaps": [f"could not load diff for {branch}: {exc}"],
                            "risk": "med",
                        })
                        continue
            spec_text = load_original_build_spec(decision_id) or spec_file.read_text(encoding="utf-8")
            results.append(check_one(decision_id, spec_text, diff_text, ops_ledger=args.ops_ledger))
        if args.json:
            print(json.dumps([r.__dict__ for r in results], indent=2, sort_keys=True))
        else:
            print(f"checked {len(results)} recent builds")
        return 1 if any(r.risk == "high" for r in results) else 0

    if not args.decision_id or not args.spec_file:
        parser.error("--decision-id and --spec-file are required unless --recent is set")
    spec_text = load_original_build_spec(args.decision_id) or args.spec_file.read_text(encoding="utf-8")
    if args.diff_file:
        diff_text = args.diff_file.read_text(encoding="utf-8")
    elif args.branch:
        diff_text = git_diff_for_branch(args.repo_root, args.branch, args.base)
    else:
        parser.error("--branch or --diff-file is required")
    result = check_one(args.decision_id, spec_text, diff_text, ops_ledger=args.ops_ledger)
    if args.json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"{args.decision_id}: matches={result.matches} risk={result.risk} gaps={len(result.gaps)}")
    return 1 if result.risk == "high" else 0


if __name__ == "__main__":
    raise SystemExit(main())
