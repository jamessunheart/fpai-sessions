#!/usr/bin/env python3
"""Scoped pytest gate for autonomous build-loop branches."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PYTEST_PYTHON = os.environ.get("BUILD_LOOP_PYTEST_PYTHON", "/opt/sh-brain-src/.venv/bin/python")
DEFAULT_TIMEOUT = int(os.environ.get("BUILD_LOOP_PYTEST_TIMEOUT", "180"))
OUTPUT_LIMIT = 12000

FAST_SMOKE_SUBSET = (
    "tools/build_loop/test_activation_policy_contract.py",
    "tools/build_loop/test_auto_merge_governance.py",
    "tools/build_loop/test_changes_rework_loop.py",
    "tools/build_loop/test_pytest_gate_contract.py",
)


def changed_files(repo_root: Path, base_ref: str, head_ref: str) -> list[str]:
    refs = [f"{base_ref}...{head_ref}", f"{base_ref}..{head_ref}"]
    for ref in refs:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--name-only", ref],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
    return []


def is_test_file(path: str) -> bool:
    name = Path(path).name
    return path.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def existing(repo_root: Path, paths: list[str]) -> list[str]:
    seen: set[str] = set()
    found: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        if (repo_root / path).is_file():
            found.append(path)
    return found


def tests_for_module(repo_root: Path, module_path: str) -> list[str]:
    path = Path(module_path)
    if path.suffix != ".py" or is_test_file(module_path):
        return []

    stem = path.stem
    parent = path.parent
    candidates = [
        parent / f"test_{stem}.py",
        parent / "tests" / f"test_{stem}.py",
        Path("tests") / f"test_{stem}.py",
    ]

    matches = [str(candidate) for candidate in candidates]
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-files",
            f":(glob)**/test_{stem}.py",
            f":(glob)**/{stem}_test.py",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        matches.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    return existing(repo_root, matches)


def select_tests(repo_root: Path, changed: list[str], smoke_subset: tuple[str, ...] = FAST_SMOKE_SUBSET) -> dict[str, Any]:
    touched_tests = existing(repo_root, [path for path in changed if is_test_file(path)])
    adjacent: list[str] = []
    for path in changed:
        adjacent.extend(tests_for_module(repo_root, path))
    smoke = existing(repo_root, list(smoke_subset))

    selected = existing(repo_root, touched_tests + adjacent + smoke)
    return {
        "changed_files": changed,
        "touched_tests": touched_tests,
        "adjacent_tests": existing(repo_root, adjacent),
        "smoke_tests": smoke,
        "selected_tests": selected,
    }


def parse_counts(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}
    for key in list(counts):
        match = re.search(rf"(\d+)\s+{key}\b", output, re.IGNORECASE)
        if match:
            counts[key] = int(match.group(1))
    return counts


def output_tail(text: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def run_pytest(
    *,
    repo_root: Path,
    pytest_python: str,
    selected_tests: list[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    if not selected_tests:
        return {
            "status": "skipped",
            "returncode": 0,
            "command": [],
            "duration_seconds": 0.0,
            "counts": parse_counts(""),
            "output_tail": "No scoped pytest targets found.",
        }

    command = [pytest_python, "-m", "pytest", "-q", "-x", "--tb=short", "-ra", *selected_tests]
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
        duration = time.monotonic() - started
        output = result.stdout or ""
        counts = parse_counts(output)
        status = "passed" if result.returncode == 0 else "failed"
        if result.returncode == 5:
            status = "skipped"
        return {
            "status": status,
            "returncode": result.returncode,
            "command": command,
            "duration_seconds": round(duration, 3),
            "counts": counts,
            "output_tail": output_tail(output),
        }
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        output = (exc.stdout or "") + (exc.stderr or "")
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {
            "status": "timed_out",
            "returncode": 124,
            "command": command,
            "duration_seconds": round(duration, 3),
            "counts": parse_counts(output),
            "output_tail": output_tail(output + f"\npytest timed out after {timeout_seconds}s\n"),
        }


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_summary(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    selected = report.get("selected_tests") or []
    lines = [
        f"PYTEST GATE {str(report.get('status', 'unknown')).upper()}",
        f"spec: {report.get('spec_id') or ''}",
        f"selected: {len(selected)} test target(s)",
        "counts: "
        f"passed={counts.get('passed', 0)} "
        f"failed={counts.get('failed', 0)} "
        f"errors={counts.get('errors', 0)} "
        f"skipped={counts.get('skipped', 0)}",
    ]
    if selected:
        lines.append("targets:")
        lines.extend(f"- {path}" for path in selected)
    output = str(report.get("output_tail") or "").strip()
    if output:
        lines.extend(["", "output tail:", output])
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base-ref", default="feat/headless-build")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--spec-id", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--python", default=DEFAULT_PYTEST_PYTHON)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    changed = changed_files(repo_root, args.base_ref, args.head_ref)
    selection = select_tests(repo_root, changed)
    pytest_result = run_pytest(
        repo_root=repo_root,
        pytest_python=args.python,
        selected_tests=selection["selected_tests"],
        timeout_seconds=args.timeout,
    )
    report = {
        "schema": "fpai_build_loop_pytest_gate_v1",
        "spec_id": args.spec_id,
        "branch": args.branch,
        "base_ref": args.base_ref,
        "head_ref": args.head_ref,
        "pytest_python": args.python,
        "timeout_seconds": args.timeout,
        **selection,
        **pytest_result,
    }
    write_report(args.output, report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_summary(report), end="")
    return 0 if report["status"] in {"passed", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
