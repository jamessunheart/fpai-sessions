from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.coherence import weekly_score

NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.timezone.utc)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.utime(path, (NOW.timestamp(), NOW.timestamp()))


class WeeklyCoherenceScoreTest(unittest.TestCase):
    def test_high_score_when_canonical_surfaces_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = (
                "Full Potential OS coherence routes upstream and downstream. "
                "Memory context, proof evidence, tested result, Resource Discipline Gate, "
                "Reserved Class, adjacent intent, unlocks next, next move."
            )
            for rel in weekly_score.SOURCE_PATHS:
                _write(root / rel, canonical)
            registry = root / "core" / "BUILD" / "REGISTRY.json"
            _write(
                registry,
                json.dumps(
                    {
                        "active_builds": [
                            {
                                "slug": "SPEC_x",
                                "status": "done",
                                "tests_passed": True,
                                "branch": "build/SPEC_x",
                                "base_branch": "feat/headless-build",
                            }
                        ]
                    }
                ),
            )

            report = weekly_score.build_report(repo_root=root, registry_path=registry, now=NOW)

        self.assertEqual(report.status, "PASS")
        self.assertGreaterEqual(report.score, 90)
        self.assertEqual(report.registry_gaps, ())

    def test_missing_surface_and_registry_gap_lower_score_with_repairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in weekly_score.SOURCE_PATHS[:3]:
                _write(root / rel, "coherence route proof memory")
            registry = root / "core" / "BUILD" / "REGISTRY.json"
            _write(
                registry,
                json.dumps(
                    {
                        "active_builds": [
                            {
                                "slug": "SPEC_dup",
                                "status": "building",
                                "tests_passed": False,
                                "branch": "build/SPEC_dup",
                                "base_branch": "feat/headless-build",
                            },
                            {
                                "slug": "SPEC_dup",
                                "status": "building",
                                "tests_passed": False,
                                "branch": "build/SPEC_dup",
                                "base_branch": "main",
                            },
                        ]
                    }
                ),
            )

            report = weekly_score.build_report(repo_root=root, registry_path=registry, now=NOW)

        self.assertLess(report.score, 80)
        self.assertTrue(any("duplicate building" in gap for gap in report.registry_gaps))
        self.assertTrue(any("base_branch is main" in gap for gap in report.registry_gaps))
        self.assertTrue(any("missing coherence surfaces" in item.lower() for item in report.recommendations))

    def test_writes_json_markdown_and_state_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in weekly_score.SOURCE_PATHS:
                _write(root / rel, "coherence route proof memory next move Resource Discipline Gate")
            registry = root / "core" / "BUILD" / "REGISTRY.json"
            _write(registry, json.dumps({"active_builds": []}))
            report = weekly_score.build_report(repo_root=root, registry_path=registry, now=NOW)

            weekly_score.write_report(
                report,
                json_path=root / "signal.json",
                markdown_path=root / "signal.md",
                state_path=root / "state.md",
            )

            payload = json.loads((root / "signal.json").read_text(encoding="utf-8"))
            markdown = (root / "state.md").read_text(encoding="utf-8")

        self.assertEqual(payload["schema"], weekly_score.SCHEMA)
        self.assertIn("# Coherence Score", markdown)
        self.assertIn("Recommended Repairs", markdown)


if __name__ == "__main__":
    unittest.main()

