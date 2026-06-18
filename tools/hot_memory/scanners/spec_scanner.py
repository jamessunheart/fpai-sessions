#!/usr/bin/env python3
"""Scan build specs and registry state into a hot-memory delta."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from tools.hot_memory.common import DEFAULT_HOT_DIR, REPO_ROOT, compact_facts, fact, file_date, read_json, write_scan


def collect(repo_root: Path = REPO_ROOT):
    registry_path = repo_root / "core" / "BUILD" / "REGISTRY.json"
    specs_dir = repo_root / "core" / "BUILD" / "specs"
    results_dir = repo_root / "core" / "BUILD" / "results"
    registry = read_json(registry_path)
    rows = registry.get("active_builds") if isinstance(registry.get("active_builds"), list) else []
    facts = []
    active = [row for row in rows if isinstance(row, dict) and row.get("status") in {"building", "queued", "ready"}]
    for row in active[:3]:
        facts.append(
            fact(
                f"Active spec {row.get('slug') or row.get('id')} is {row.get('status')} on {row.get('branch')}",
                f"core/BUILD/REGISTRY.json",
                file_date(registry_path),
                weight=9,
                category="spec_queue",
            )
        )
    for row in rows:
        if isinstance(row, dict) and row.get("status") == "done":
            facts.append(
                fact(
                    f"Last built spec is {row.get('slug') or row.get('id')} on {row.get('branch')}",
                    "core/BUILD/REGISTRY.json",
                    file_date(registry_path),
                    weight=7,
                    category="spec_queue",
                )
            )
            break
    pending = []
    if specs_dir.exists():
        for spec in sorted(specs_dir.glob("SPEC_*.md")):
            if not (results_dir / f"{spec.stem}.result.md").exists():
                pending.append(spec.stem)
    if pending:
        facts.append(
            fact(
                f"Top pending build specs: {', '.join(pending[:3])}",
                "core/BUILD/specs",
                file_date(max((specs_dir / f'{name}.md' for name in pending[:3]), key=lambda path: path.stat().st_mtime)),
                weight=6,
                category="spec_queue",
            )
        )
    merged = _last_merge(repo_root)
    if merged:
        facts.append(fact(f"Last git merge/build marker: {merged}", "git log", file_date(repo_root / ".git"), weight=5, category="spec_queue"))
    return compact_facts(facts, limit=10)


def _last_merge(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1", "--merges"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    args = parser.parse_args(argv)
    payload = write_scan("spec", collect(args.repo_root), hot_dir=args.hot_dir)
    print(payload["changed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

