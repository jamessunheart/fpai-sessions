#!/usr/bin/env python3
"""Canonical build-state helpers for build-loop status surfaces.

The build loop has several status surfaces: repo-local specs/results,
REGISTRY.json, and brain_index.decisions. This module owns the shared
"queued vs built" predicates so those surfaces do not drift apart.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPECS_DIR = REPO_ROOT / "core" / "BUILD" / "specs"
DEFAULT_RESULTS_DIR = REPO_ROOT / "core" / "BUILD" / "results"
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"

BUILT_DECISION_STATUSES = {
    "built",
    "changes",
    "merge_requested",
    "merged",
    "merge_failed",
    "rejected",
}

PENDING_DECISION_WHERE_SQL = """
         WHERE status = 'answered'
           AND COALESCE(needs_build, false) = true
           AND COALESCE(spec_written, false) = false
           AND COALESCE(is_canary, false) = false
           AND lower(COALESCE(build_status, '')) NOT IN (
               'built',
               'changes',
               'merge_requested',
               'merged',
               'merge_failed',
               'rejected'
           )
"""


@dataclasses.dataclass(frozen=True)
class RepoBuildState:
    queued_specs: list[str]
    built_results: list[str]
    registry_building: list[str]
    registry_done: list[str]

    @property
    def queued_count(self) -> int:
        return len(self.queued_specs)

    @property
    def built_count(self) -> int:
        return len(self.built_results)

    def payload(self) -> dict[str, Any]:
        return {
            "queued_count": self.queued_count,
            "built_count": self.built_count,
            "queued_specs": self.queued_specs,
            "built_results": self.built_results,
            "registry_building": self.registry_building,
            "registry_done": self.registry_done,
        }


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def decision_build_status(row: dict[str, Any]) -> str:
    return str(row.get("build_status") or "").strip().lower()


def is_decision_pending_build(row: dict[str, Any]) -> bool:
    if str(row.get("status") or "").strip().lower() != "answered":
        return False
    if not boolish(row.get("needs_build")):
        return False
    if boolish(row.get("spec_written")):
        return False
    if boolish(row.get("is_canary")):
        return False
    if decision_build_status(row) in BUILT_DECISION_STATUSES:
        return False
    return True


def pending_builds_from_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if is_decision_pending_build(row)]


def collect_repo_build_state(
    specs_dir: Path | str = DEFAULT_SPECS_DIR,
    results_dir: Path | str = DEFAULT_RESULTS_DIR,
    registry_path: Path | str = DEFAULT_REGISTRY,
) -> RepoBuildState:
    specs = Path(specs_dir)
    results = Path(results_dir)
    registry = Path(registry_path)
    queued: list[str] = []
    built: list[str] = []

    if specs.exists():
        for spec in sorted(specs.glob("*.md")):
            spec_id = spec.stem
            result = results / f"{spec_id}.result.md"
            if result.exists():
                built.append(spec_id)
            else:
                queued.append(spec_id)

    registry_building: list[str] = []
    registry_done: list[str] = []
    if registry.exists():
        try:
            data = json.loads(registry.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for item in data.get("active_builds", []):
            build_id = str(item.get("id") or item.get("slug") or "").strip()
            if not build_id:
                continue
            status = str(item.get("status") or "").strip().lower()
            if status == "building":
                registry_building.append(build_id)
            elif status in {"done", "merged"}:
                registry_done.append(build_id)

    return RepoBuildState(
        queued_specs=queued,
        built_results=built,
        registry_building=registry_building,
        registry_done=registry_done,
    )


def render_text(state: RepoBuildState) -> str:
    lines = [
        f"Build state: queued={state.queued_count} built={state.built_count}",
        "",
        "Queued specs",
        "------------",
    ]
    lines.extend(state.queued_specs or ["(none)"])
    lines.extend(["", "Built results", "-------------"])
    lines.extend(state.built_results[-10:] or ["(none)"])
    lines.extend(["", "Registry building", "-----------------"])
    lines.extend(state.registry_building or ["(none)"])
    lines.extend(["", "Registry done/merged", "--------------------"])
    lines.extend(state.registry_done[:20] or ["(none)"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = args.repo
    state = collect_repo_build_state(
        specs_dir=repo / "core" / "BUILD" / "specs",
        results_dir=repo / "core" / "BUILD" / "results",
        registry_path=repo / "core" / "BUILD" / "REGISTRY.json",
    )
    if args.json:
        print(json.dumps(state.payload(), indent=2, sort_keys=True))
    else:
        print(render_text(state), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
