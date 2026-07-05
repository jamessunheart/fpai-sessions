#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_loop import build_state


class BuildStateTest(unittest.TestCase):
    def test_pending_builds_filter_excludes_canary_and_built_statuses(self) -> None:
        rows = [
            {"id": "d001", "status": "answered", "needs_build": True, "spec_written": False},
            {"id": "d002", "status": "answered", "needs_build": True, "spec_written": False, "is_canary": True},
            {"id": "d003", "status": "answered", "needs_build": True, "spec_written": False, "build_status": "built"},
            {"id": "d004", "status": "answered", "needs_build": True, "spec_written": False, "build_status": "changes"},
            {"id": "d005", "status": "awaiting", "needs_build": True, "spec_written": False},
        ]

        pending = build_state.pending_builds_from_rows(rows)

        self.assertEqual([row["id"] for row in pending], ["d001"])
        self.assertNotIn("COALESCE(is_canary, false) = false", build_state.PENDING_DECISION_WHERE_SQL)
        self.assertIn("'built'", build_state.PENDING_DECISION_WHERE_SQL)
        self.assertIn("'changes'", build_state.PENDING_DECISION_WHERE_SQL)

    def test_collect_repo_build_state_counts_specs_and_results_once(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-build-state-"))
        specs = root / "core" / "BUILD" / "specs"
        results = root / "core" / "BUILD" / "results"
        specs.mkdir(parents=True)
        results.mkdir(parents=True)
        (specs / "SPEC_a.md").write_text("# a\n", encoding="utf-8")
        (specs / "SPEC_b.md").write_text("# b\n", encoding="utf-8")
        (results / "SPEC_b.result.md").write_text("done\n", encoding="utf-8")
        registry = root / "core" / "BUILD" / "REGISTRY.json"
        registry.write_text(
            json.dumps(
                {
                    "active_builds": [
                        {"id": "SPEC_a", "status": "building"},
                        {"id": "SPEC_b", "status": "done"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        state = build_state.collect_repo_build_state(specs, results, registry)

        self.assertEqual(state.queued_specs, ["SPEC_a"])
        self.assertEqual(state.built_results, ["SPEC_b"])
        self.assertEqual(state.queued_count, 1)
        self.assertEqual(state.built_count, 1)
        self.assertEqual(state.registry_building, ["SPEC_a"])
        self.assertEqual(state.registry_done, ["SPEC_b"])

    def test_render_text_uses_canonical_summary_line(self) -> None:
        state = build_state.RepoBuildState(
            queued_specs=["SPEC_a"],
            built_results=["SPEC_b"],
            registry_building=[],
            registry_done=[],
        )

        text = build_state.render_text(state)

        self.assertIn("Build state: queued=1 built=1", text)
        self.assertIn("Queued specs", text)
        self.assertIn("Built results", text)


if __name__ == "__main__":
    unittest.main()
