from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.state_reconciler import status


class StateStatusTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-state-status-"))
        (root / "docs" / "codex" / "specs").mkdir(parents=True)
        (root / "docs" / "codex" / "INTENT_BUILDSTREAM.md").write_text(
            "\n".join(
                [
                    "- Rung 0 | id: rung0-reserved-class-boundary | route: codex | status: ready | next: boundary",
                    "- Rung 1 | id: rung1-apprentice-execution-tier | route: codex | status: blocked-on-rung0 | next: apprentice",
                    "- Rung 2 | id: rung2-self-directing-loop | route: codex | status: blocked-on-rung1 | next: loop",
                    "- Rung 3 | id: rung3-auto-spec-drafting | route: codex | status: blocked-on-rung2 | next: specs",
                    "- Rung 4 | id: rung4-hubs | route: apprentice | status: blocked-on-rung3 | next: hubs",
                ]
            ),
            encoding="utf-8",
        )
        (root / "docs" / "codex" / "HANDOFF.md").write_text(
            "\n".join(
                [
                    "### 2026-06-09 · SPEC_reserved-class-boundary · branch `feat/headless-build`",
                    "### 2026-06-10 · SPEC_apprentice-execution-tier · branch `feat/headless-build`",
                    "### 2026-06-10 · SPEC_self-directing-loop · branch `feat/headless-build`",
                ]
            ),
            encoding="utf-8",
        )
        (root / "tools" / "reserved").mkdir(parents=True)
        (root / "tools" / "reserved" / "classify.py").write_text("# reserved\n", encoding="utf-8")
        (root / "tools" / "apprentice").mkdir(parents=True)
        (root / "tools" / "apprentice" / "run.py").write_text("# apprentice\n", encoding="utf-8")
        (root / "tools" / "loop").mkdir(parents=True)
        (root / "tools" / "loop" / "direct.py").write_text("# loop\n", encoding="utf-8")
        (root / "docs" / "codex" / "specs" / "SPEC_auto-spec-drafting.md").write_text(
            "# SPEC_auto-spec-drafting\n",
            encoding="utf-8",
        )
        return root

    def test_summarize_detects_ladder_drift_and_next_unlock(self) -> None:
        repo = self.make_repo()

        report = status.summarize(repo)

        self.assertEqual(report.rungs[0].actual_state, "built")
        self.assertEqual(report.rungs[1].actual_state, "built")
        self.assertEqual(report.rungs[2].actual_state, "built")
        self.assertEqual(report.rungs[3].actual_state, "ready")
        self.assertTrue(any("Rung 3" in drift for drift in report.drifts))
        self.assertIn("SPEC_auto-spec-drafting", report.next_unlock)

    def test_render_markdown_includes_vault_mirror_guidance(self) -> None:
        repo = self.make_repo()
        report = status.summarize(repo)

        markdown = status.render_markdown(report)

        self.assertIn("# Codex State Status", markdown)
        self.assertIn("## Vault Mirror", markdown)
        self.assertIn("[[CODEX STATE STATUS]]", markdown)
        self.assertIn("Suggested HANDOFF Note", markdown)

    def test_unlogged_auto_spec_artifacts_pause_before_next_rung(self) -> None:
        repo = self.make_repo()
        (repo / "tools" / "spec").mkdir(parents=True)
        (repo / "tools" / "spec" / "draft.py").write_text("# draft\n", encoding="utf-8")
        (repo / "docs" / "codex" / "specs" / "SPEC_rung4-hubs.draft.md").write_text(
            "# draft\n",
            encoding="utf-8",
        )

        report = status.summarize(repo)

        self.assertEqual(report.rungs[3].actual_state, "artifact-present-unlogged")
        self.assertIn("Review/log Rung 3", report.next_unlock)
        self.assertTrue(any("no HANDOFF completion marker" in drift for drift in report.drifts))

    def test_write_report_is_explicit(self) -> None:
        repo = self.make_repo()
        report = status.summarize(repo)
        path = repo / "docs" / "codex" / "STATE_STATUS.md"

        written = status.write_report(report, path)

        self.assertEqual(written, path)
        self.assertIn("Codex State Status", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
