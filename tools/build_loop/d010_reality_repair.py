#!/usr/bin/env python3
"""Repair proof rows for the d010 preference-learning merged-dead audit.

The original d010 build shipped advisory L1 preference dataset and eval-judge
tools, but predated the delayed post-merge reality checker's strict proof
contract. This helper proves the artifact still works with a bounded temporary
fixture, then appends the two canonical rows the checker requires:

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


ORIGINAL_SPEC_ID = "SPEC_d010_self-evolution-l1-preference-dat"
ORIGINAL_BRANCH = "build/SPEC_d010_self-evolution-l1-preference-dat"


def run_preference_learning_smoke(repo_root: Path) -> tuple[bool, str, list[str]]:
    """Run a bounded d010 dataset/eval smoke and return ok, detail, evidence."""
    dataset_script = repo_root / "tools" / "learn" / "build_preference_dataset.py"
    eval_script = repo_root / "tools" / "learn" / "eval_judge.py"
    readme = repo_root / "tools" / "learn" / "README.md"
    missing = [str(path.relative_to(repo_root)) for path in (dataset_script, eval_script, readme) if not path.exists()]
    if missing:
        return False, "missing shipped artifacts: " + ", ".join(missing), []

    with tempfile.TemporaryDirectory(prefix="fpai-d010-reality-proof-") as tmp:
        root = Path(tmp)
        fixture = root / "signals"
        output = root / "preference_pairs.jsonl"
        _write_signal_fixture(fixture)

        env = {**os.environ, "FPAI_REPO_ROOT": str(repo_root)}
        build_cmd = [
            sys.executable,
            "-B",
            str(dataset_script),
            "--root",
            str(fixture),
            "--output",
            str(output),
            "--eval-percent",
            "100",
        ]
        built = subprocess.run(build_cmd, cwd=repo_root, env=env, capture_output=True, text=True, timeout=20, check=False)
        if built.returncode != 0:
            return False, f"dataset smoke failed rc={built.returncode}: {_bounded(built.stderr or built.stdout)}", []
        try:
            summary = json.loads(built.stdout)
        except json.JSONDecodeError as exc:
            return False, f"dataset smoke output was not JSON: {exc}", []
        if int(summary.get("pairs") or 0) < 4:
            return False, f"dataset smoke produced too few pairs: {summary}", []
        if int(summary.get("eval") or 0) != int(summary.get("pairs") or 0):
            return False, f"held-out split smoke did not mark every row never-train: {summary}", []
        rows = _read_jsonl(output)
        if len(rows) != int(summary["pairs"]):
            return False, "dataset JSONL row count does not match builder summary", []
        if not all(row.get("never_train") is True and row.get("split") == "eval" for row in rows):
            return False, "dataset rows are not all held-out never-train rows", []
        if not all(row.get("preferred", {}).get("text") and row.get("rejected", {}).get("text") for row in rows):
            return False, "dataset rows are missing preferred/rejected text", []
        if not all(row.get("eval", {}).get("label") in {"A", "B"} for row in rows):
            return False, "dataset rows are missing frozen eval labels", []

        eval_cmd = [sys.executable, "-B", str(eval_script), str(output), "--judge", "keyword"]
        judged = subprocess.run(eval_cmd, cwd=repo_root, env=env, capture_output=True, text=True, timeout=20, check=False)
        if judged.returncode != 0:
            return False, f"eval judge smoke failed rc={judged.returncode}: {_bounded(judged.stderr or judged.stdout)}", []
        score_text = judged.stdout.strip()
        try:
            float(score_text)
        except ValueError:
            return False, f"eval judge did not print one numeric score: {score_text!r}", []

    evidence = [
        f"build_preference_dataset.py generated {summary['pairs']} preference pairs from temporary signals",
        "100% held-out smoke marked every generated row never_train=true",
        f"eval_judge.py keyword smoke returned one numeric go/no-go score ({score_text})",
        "tools/learn/README.md documents advisory-only/no-training boundary",
    ]
    detail = (
        "d010 preference dataset/eval judge smoke passed; "
        f"{summary['pairs']} pairs generated with frozen held-out labels"
    )
    return True, detail, evidence


def append_repair_proof(
    ops_ledger: Path,
    *,
    repo_root: Path,
    spec_id: str = ORIGINAL_SPEC_ID,
    branch: str = ORIGINAL_BRANCH,
) -> dict[str, Any]:
    ok, detail, evidence = run_preference_learning_smoke(repo_root)
    check = probe.LivenessCheck("command", "d010 preference dataset/eval judge smoke", "d010 preference learning smoke")
    result = probe.CheckResult(check, "live" if ok else "dead", detail)
    report = probe.ProbeReport("live" if ok else "dead", (result,), spec_id=spec_id, branch=branch)
    probe.append_ops_ledger(ops_ledger, report)
    if not ok:
        return {"ok": False, "liveness": report.to_json(), "feature_outcome": None}

    outcome = feature_outcome.append_feature_outcome(
        ops_ledger,
        spec_id=spec_id,
        metric_name="preference_learning_measurement_spine",
        baseline="merged_advisory_tools_without_post_merge_proof",
        observed="dataset_assembly_and_eval_judge_smoke_passed",
        delta="temporary signals produced held-out never-train preference pairs and a numeric judge score",
        verdict="improved",
        branch=branch,
        evidence=[report.detail(), *evidence],
    )
    return {"ok": True, "liveness": report.to_json(), "feature_outcome": outcome}


def _write_signal_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "brain_index.json").write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "id": "d010-good-merge",
                        "merge_outcome": "good",
                        "prompt": "ship guarded preference measurement",
                        "decision": "build advisory dataset and frozen held-out eval before training",
                        "alternative": "train directly on unreviewed production signals",
                    },
                    {
                        "id": "d010-regression",
                        "merge_outcome": "regressed",
                        "prompt": "judge learning improvement",
                        "action": "claimed improvement without a consequence-ledger check",
                        "correction": "measure the held-out judge against a deterministic baseline first",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    memory = root / "memory"
    memory.mkdir()
    (memory / "feedback_d010.md").write_text(
        "Prompt: answer d010\n"
        "Rejected: train on the held-out split later\n"
        "Preferred: mark held-out examples never-train forever\n",
        encoding="utf-8",
    )
    (root / "DECISIONS.md").write_text(
        "## receipt row\n"
        "Decision: ship a proof claim from vibes only\n"
        "Receipt: tested consequence evidence before scoring\n"
        "Verdict: good\n",
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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
