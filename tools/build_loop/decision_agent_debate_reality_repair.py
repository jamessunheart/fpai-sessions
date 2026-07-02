#!/usr/bin/env python3
"""Repair proof rows for the decision-agent debate.py merged-dead audit.

The original build hardened ``tools/council/debate.py`` so failing council
voices degrade transparently instead of crashing every run. This helper proves
that behavior with injected failing runners, then appends the two canonical
rows the post-merge reality checker requires for the original spec:

- liveness:pass
- feature_outcome with verdict=improved
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from tools.build_loop import feature_outcome
from tools.liveness import probe


ORIGINAL_SPEC_ID = "SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot"
ORIGINAL_BRANCH = "build/SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot"


def run_debate_failure_isolation_smoke(repo_root: Path) -> tuple[bool, str, list[str]]:
    """Exercise the shipped debate wrapper behavior without live CLI calls."""
    debate_path = repo_root / "tools" / "council" / "debate.py"
    if not debate_path.exists():
        return False, "missing shipped artifact: tools/council/debate.py", []

    try:
        from tools.council import debate
    except Exception as exc:
        return False, f"could not import tools.council.debate: {type(exc).__name__}: {exc}", []

    ops: list[tuple[str, str]] = []

    def fake_ops(event: str, detail: str, nxt: str = "") -> None:
        ops.append((event, detail))

    def failing_codex_runner(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 2, "", "codex auth missing")

    def wrapped_json_runner(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, 'thinking...\n{"propose": false, "title": "No build"}\n', "")

    def failing_claude_runner(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "claude auth missing")

    def failing_glm(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("glm unavailable")

    old_ops = debate._ops
    old_which = debate.shutil.which
    debate._ops = fake_ops
    debate.shutil.which = lambda _name: "/usr/bin/fake"
    try:
        gpt = debate.gpt_voice("queue", runner=failing_codex_runner)
        pragmatist = debate.pragmatist_voice("queue", glm_caller=failing_glm)
        parsed, claude_result = debate.run_claude_json("prompt", runner=wrapped_json_runner)
        try:
            debate.run_claude_json("prompt", runner=failing_claude_runner)
        except RuntimeError as exc:
            claude_failure = str(exc)
        else:
            return False, "claude failure runner did not raise", []
    finally:
        debate._ops = old_ops
        debate.shutil.which = old_which

    expected_events = {event for event, _detail in ops}
    checks = [
        (gpt == "", "codex voice failure returned empty fallback"),
        ("gpt_voice_error" in expected_events, "codex voice failure logged gpt_voice_error"),
        (pragmatist == "", "glm pragmatist failure returned empty fallback"),
        ("pragmatist_voice_error" in expected_events, "glm failure logged pragmatist_voice_error"),
        (parsed.get("propose") is False and claude_result.returncode == 0, "claude wrapper parsed wrapped JSON"),
        ("claude auth missing" in claude_failure, "claude wrapper raised transparent CLI failure"),
    ]
    failed = [label for ok, label in checks if not ok]
    if failed:
        return False, "debate failure-isolation smoke failed: " + "; ".join(failed), []

    evidence = [label for _ok, label in checks]
    detail = "debate voice wrappers isolated codex/glm failures and reported claude failure transparently"
    return True, detail, evidence


def append_repair_proof(
    ops_ledger: Path,
    *,
    repo_root: Path,
    spec_id: str = ORIGINAL_SPEC_ID,
    branch: str = ORIGINAL_BRANCH,
) -> dict[str, Any]:
    ok, detail, evidence = run_debate_failure_isolation_smoke(repo_root)
    check = probe.LivenessCheck("command", "decision debate voice failure-isolation smoke", "decision debate smoke")
    result = probe.CheckResult(check, "live" if ok else "dead", detail)
    report = probe.ProbeReport("live" if ok else "dead", (result,), spec_id=spec_id, branch=branch)
    probe.append_ops_ledger(ops_ledger, report)
    if not ok:
        return {"ok": False, "liveness": report.to_json(), "feature_outcome": None}

    outcome = feature_outcome.append_feature_outcome(
        ops_ledger,
        spec_id=spec_id,
        metric_name="decision_debate_voice_failure_isolation",
        baseline="voice_failures_crash_or_hide_errors",
        observed="codex_and_glm_failures_log_and_skip_while_claude_failure_reports_clearly",
        delta="injected failure smoke passed across codex, glm, and claude debate wrappers",
        verdict="improved",
        branch=branch,
        evidence=[report.detail(), *evidence],
    )
    return {"ok": True, "liveness": report.to_json(), "feature_outcome": outcome}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--ops-ledger", type=Path, default=feature_outcome.DEFAULT_OPS_LEDGER)
    parser.add_argument("--spec-id", default=ORIGINAL_SPEC_ID)
    parser.add_argument("--branch", default=ORIGINAL_BRANCH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = append_repair_proof(args.ops_ledger, repo_root=args.repo_root, spec_id=args.spec_id, branch=args.branch)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
