#!/usr/bin/env python3
"""Update tools/test/expected_outputs.json after a build merge."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUTS = REPO_ROOT / "tools" / "test" / "expected_outputs.json"
EXCLUDED_PREFIXES = (
    "core/BUILD/",
    "docs/codex/HANDOFF.md",
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


def extract_paths_from_name_status(diff_text: str) -> list[str]:
    paths: list[str] = []
    for raw in diff_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("D"):
            continue
        if status.startswith("R") and len(parts) >= 3:
            path = parts[2]
        elif status[:1] in {"A", "M", "C"} and len(parts) >= 2:
            path = parts[1]
        else:
            continue
        if should_record_path(path):
            paths.append(path)
    return sorted(set(paths))


def should_record_path(path: str) -> bool:
    if not path or path.endswith("/"):
        return False
    if path.startswith("core/BUILD/systemd/"):
        return True
    return not any(path == prefix or path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def diff_name_status(repo_root: Path, branch: str, base: str = "feat/headless-build") -> str:
    merge_base = subprocess.check_output(
        ["git", "-C", str(repo_root), "merge-base", base, branch],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "diff", "--name-status", merge_base, branch],
        text=True,
        stderr=subprocess.DEVNULL,
    )


def update_expected_outputs(
    decision_id: str,
    paths: list[str],
    *,
    expected_outputs: Path = DEFAULT_OUTPUTS,
) -> dict[str, list[str]]:
    did = normalize_decision_id(decision_id)
    try:
        data = json.loads(expected_outputs.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
    merged = sorted(set(data.get(did, [])) | set(paths))
    data[did] = merged
    expected_outputs.parent.mkdir(parents=True, exist_ok=True)
    expected_outputs.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record build output files for smoke test 7")
    parser.add_argument("decision_id")
    parser.add_argument("branch")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base", default="feat/headless-build")
    parser.add_argument("--expected-outputs", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--diff-file", type=Path, help="test helper: read git name-status text from file")
    args = parser.parse_args(argv)

    diff_text = args.diff_file.read_text(encoding="utf-8") if args.diff_file else diff_name_status(args.repo_root, args.branch, args.base)
    paths = extract_paths_from_name_status(diff_text)
    update_expected_outputs(args.decision_id, paths, expected_outputs=args.expected_outputs)
    print(f"{normalize_decision_id(args.decision_id)}: recorded {len(paths)} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
