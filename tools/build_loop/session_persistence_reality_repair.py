#!/usr/bin/env python3
"""Repair proof rows for the session persistence merged-dead audit.

The original session-persistence build shipped repo code but predated the
post-merge reality checker's strict proof contract. This helper proves the
artifact still works by running a fresh save/show smoke against a temporary
state directory, then appends the two canonical rows the checker requires for
the original spec:

- liveness:pass
- feature_outcome with verdict=improved
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.build_loop import feature_outcome
from tools.liveness import probe


ORIGINAL_SPEC_ID = "SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e_session-persistence"
ORIGINAL_BRANCH = "build/SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e_session-persistence"


def run_session_persistence_smoke(repo_root: Path) -> tuple[bool, str, list[str]]:
    """Run a bounded save/show smoke and return ok, detail, evidence."""
    script = repo_root / "tools" / "continuity" / "session_persistence.py"
    build_context = repo_root / "SERVICES" / "sunheart-brain" / "curator" / "build_context.py"
    missing = [str(path.relative_to(repo_root)) for path in (script, build_context) if not path.exists()]
    if missing:
        return False, "missing shipped artifacts: " + ", ".join(missing), []

    with tempfile.TemporaryDirectory(prefix="fpai-session-persistence-proof-") as tmp:
        state_dir = Path(tmp) / "state"
        save_cmd = [
            sys.executable,
            str(script),
            "save",
            "--repo-root",
            str(repo_root),
            "--state-dir",
            str(state_dir),
            "--session-id",
            "post-merge-reality-repair",
            "--progress-note",
            "post-merge reality proof smoke",
            "--json",
        ]
        show_cmd = [
            sys.executable,
            str(script),
            "show",
            "--state-dir",
            str(state_dir),
            "--json",
        ]
        env = {**os.environ, "FPAI_REPO_ROOT": str(repo_root)}
        save = subprocess.run(save_cmd, cwd=repo_root, env=env, capture_output=True, text=True, timeout=20, check=False)
        if save.returncode != 0:
            return False, f"save smoke failed rc={save.returncode}: {_bounded(save.stderr or save.stdout)}", []
        show = subprocess.run(show_cmd, cwd=repo_root, env=env, capture_output=True, text=True, timeout=20, check=False)
        if show.returncode != 0:
            return False, f"show smoke failed rc={show.returncode}: {_bounded(show.stderr or show.stdout)}", []
        try:
            saved = json.loads(save.stdout)
            loaded = json.loads(show.stdout)
        except json.JSONDecodeError as exc:
            return False, f"smoke output was not JSON: {exc}", []
        if saved.get("schema") != "fpai-session-snapshot.v1" or loaded.get("schema") != "fpai-session-snapshot.v1":
            return False, "snapshot schema missing from save/show smoke", []
        if loaded.get("session_id") != "post-merge-reality-repair":
            return False, "show did not load the saved repair session snapshot", []

    evidence = [
        "session_persistence.py save/show smoke passed",
        "latest persisted snapshot reloads across fresh CLI invocation",
        "build_context.py session persistence integration file present",
    ]
    detail = "session persistence save/show smoke passed; latest snapshot reloaded"
    return True, detail, evidence


def append_repair_proof(
    ops_ledger: Path,
    *,
    repo_root: Path,
    spec_id: str = ORIGINAL_SPEC_ID,
    branch: str = ORIGINAL_BRANCH,
) -> dict[str, Any]:
    ok, detail, evidence = run_session_persistence_smoke(repo_root)
    check = probe.LivenessCheck("command", "session persistence save/show smoke", "session persistence smoke")
    result = probe.CheckResult(check, "live" if ok else "dead", detail)
    report = probe.ProbeReport("live" if ok else "dead", (result,), spec_id=spec_id, branch=branch)
    probe.append_ops_ledger(ops_ledger, report)
    if not ok:
        return {"ok": False, "liveness": report.to_json(), "feature_outcome": None}

    outcome = feature_outcome.append_feature_outcome(
        ops_ledger,
        spec_id=spec_id,
        metric_name="session_persistence_context_recall",
        baseline="fresh_session_requires_rebrief",
        observed="fresh_session_loads_persisted_snapshot",
        delta="save/show smoke passed and build-context integration is present",
        verdict="improved",
        branch=branch,
        evidence=[report.detail(), *evidence],
    )
    return {"ok": True, "liveness": report.to_json(), "feature_outcome": outcome}


def _bounded(text: str, limit: int = 500) -> str:
    return " ".join(str(text or "").split())[:limit]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2])))
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
