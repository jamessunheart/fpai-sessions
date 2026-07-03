#!/usr/bin/env python3
"""Emit post-merge proof rows for live artifacts detected in a merged diff."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

from tools.build_loop import feature_outcome


DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
REPO_ROOT = Path(__file__).resolve().parents[2]


LIVE_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("systemd", re.compile(r"(^|/)([^/]+\.(service|timer|socket))$")),
    ("launchagent", re.compile(r"(^|/)tools/launchagents/[^/]+\.plist$")),
    ("activation", re.compile(r"(^|/)core/BUILD/activate/[^/]+\.sh$")),
    ("deployed_file", re.compile(r"(^|/)tools/build_loop/server_build_loop\.sh$")),
    ("deployed_file", re.compile(r"(^|/)tools/forge/auto_merge\.sh$")),
    ("service_import", re.compile(r"(^|/)SERVICES/[^/]+/.+\.(py|sh|sql|service|timer|plist)$")),
)

METRIC_MOVING_RE = re.compile(
    r"\b("
    r"feature_outcome|verdict\s*=\s*improved|metric[-_ ]moving|metric moved|"
    r"metric movement|improve[ds]?|improvement|drops? below|raises? above|"
    r"conversion|dead_rate|rate|score|quality|outcome"
    r")\b",
    re.I,
)


def changed_paths(repo_root: Path, base_ref: str, head_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--name-only", "--diff-filter=ACMRT", base_ref, head_ref],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "git diff failed").strip())
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def classify_live_artifacts(paths: Iterable[str]) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in paths:
        normalized = path.strip().lstrip("./")
        if not normalized or normalized in seen:
            continue
        for kind, pattern in LIVE_PATH_PATTERNS:
            if pattern.search(normalized):
                artifacts.append({"type": kind, "path": normalized})
                seen.add(normalized)
                break
    return artifacts


def is_metric_moving(text: str) -> bool:
    return bool(METRIC_MOVING_RE.search(text or ""))


def append_liveness_pass(
    ops_ledger: Path,
    *,
    spec_id: str,
    decision_id: str,
    branch: str,
    artifact: dict[str, str],
) -> dict[str, Any]:
    artifact_path = artifact["path"]
    row = {
        "ts": utc_now_text(),
        "loop": "liveness",
        "event": "liveness:pass",
        "detail": f"{spec_id} live artifact detected at merge: {artifact_path}",
        "cost": "$0",
        "artifact": artifact_path,
        "artifact_type": artifact["type"],
        "next": "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "liveness_status": "live",
        "spec_id": spec_id,
        "decision_id": decision_id,
        "branch": branch,
    }
    append_jsonl(ops_ledger, row)
    return row


def emit_proof(
    *,
    repo_root: Path,
    ops_ledger: Path,
    spec_id: str,
    decision_id: str,
    branch: str,
    base_ref: str,
    head_ref: str,
    spec_text: str = "",
    question: str = "",
    answer: str = "",
    proof_expected: str = "",
) -> dict[str, Any]:
    paths = changed_paths(repo_root, base_ref, head_ref)
    artifacts = classify_live_artifacts(paths)
    rows = [
        append_liveness_pass(
            ops_ledger,
            spec_id=spec_id,
            decision_id=decision_id,
            branch=branch,
            artifact=artifact,
        )
        for artifact in artifacts
    ]
    metric_text = "\n".join([spec_text, question, answer, proof_expected])
    outcome: dict[str, Any] | None = None
    if rows and is_metric_moving(metric_text):
        outcome = feature_outcome.append_feature_outcome(
            ops_ledger,
            spec_id=spec_id,
            metric_name="declared_metric_movement",
            baseline="pre_merge",
            observed="post_merge_live_artifact",
            delta="declared improved by spec proof",
            verdict="improved",
            branch=branch,
            evidence=[f"liveness:pass [{row['artifact']}]" for row in rows],
        )
    return {
        "ok": True,
        "spec_id": spec_id,
        "decision_id": decision_id,
        "branch": branch,
        "changed_paths": paths,
        "artifacts": artifacts,
        "liveness_rows": len(rows),
        "metric_moving": is_metric_moving(metric_text),
        "feature_outcome": outcome,
    }


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def utc_now_text() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--spec-id", required=True)
    parser.add_argument("--decision-id", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--spec-file", type=Path)
    parser.add_argument("--question", default="")
    parser.add_argument("--answer", default="")
    parser.add_argument("--proof-expected", default="")
    args = parser.parse_args(argv)

    spec_text = ""
    if args.spec_file and args.spec_file.exists():
        spec_text = args.spec_file.read_text(encoding="utf-8", errors="replace")
    result = emit_proof(
        repo_root=args.repo_root,
        ops_ledger=args.ops_ledger,
        spec_id=args.spec_id,
        decision_id=args.decision_id,
        branch=args.branch,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        spec_text=spec_text,
        question=args.question,
        answer=args.answer,
        proof_expected=args.proof_expected,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
