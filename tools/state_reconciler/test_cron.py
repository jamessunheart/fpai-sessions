from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.queue.build import load_queue
from tools.state_reconciler import cron


class DriftCronTest(unittest.TestCase):
    def make_repo(self, now_date: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-drift-cron-"))
        (root / "core" / "STATE").mkdir(parents=True)
        (root / "core" / "STATE" / "NOW.md").write_text(
            f"# CURRENT_STATE\n\n**Last Updated:** {now_date}\n",
            encoding="utf-8",
        )
        (root / "docs" / "codex" / "specs").mkdir(parents=True)
        (root / "docs" / "codex" / "INTENT_BUILDSTREAM.md").write_text(
            "\n".join(
                [
                    "- Rung 0 | id: rung0-reserved-class-boundary | route: codex | status: built | stream: Game | next: boundary",
                    "- Rung 1 | id: rung1-apprentice-execution-tier | route: codex | status: built | stream: Game | next: apprentice",
                    "- Rung 2 | id: rung2-self-directing-loop | route: codex | status: built | stream: Game | next: loop",
                    "- Rung 3 | id: rung3-auto-spec-drafting | route: codex | status: built | stream: Game | next: specs",
                    "- Rung 4 | id: rung4-hubs | route: apprentice | status: ready | stream: Game | next: hubs",
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
                    "### 2026-06-10 · SPEC_auto-spec-drafting · branch `feat/headless-build`",
                    "- **Tests:** marker for SPEC_auto-spec-drafting · done",
                ]
            ),
            encoding="utf-8",
        )
        for rel_path in (
            "tools/reserved/classify.py",
            "tools/apprentice/run.py",
            "tools/loop/direct.py",
            "tools/spec/draft.py",
            "tools/spec/test_draft.py",
            "docs/codex/specs/SPEC_auto-spec-drafting.md",
        ):
            path = root / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fixture\n", encoding="utf-8")
        return root

    def test_fresh_ssot_reports_without_gate(self) -> None:
        repo = self.make_repo("2026-06-10")
        queue = repo / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"

        result = cron.report(repo=repo, queue_path=queue, dry_run=False, today=dt.date(2026, 6, 10))

        self.assertIsNone(result.gate)
        self.assertTrue(any(finding.code == "now_fresh" for finding in result.findings))
        self.assertTrue((repo / "docs" / "codex" / "STATE_STATUS.md").exists())
        self.assertFalse(queue.exists())

    def test_stale_ssot_opens_exactly_one_deduped_gate(self) -> None:
        repo = self.make_repo("2026-06-01")
        queue = repo / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"

        first = cron.report(repo=repo, queue_path=queue, dry_run=False, today=dt.date(2026, 6, 10))
        second = cron.report(repo=repo, queue_path=queue, dry_run=False, today=dt.date(2026, 6, 10))

        self.assertEqual(first.gate["id"], cron.NOW_STALE_GATE_ID)
        self.assertEqual(second.gate["id"], cron.NOW_STALE_GATE_ID)
        gates = load_queue(queue)["gates"]
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0]["question"], "NOW.md is 9 days stale - refresh the state SSOT?")
        self.assertIn("now_stale", (repo / "docs" / "codex" / "STATE_STATUS.md").read_text(encoding="utf-8"))

    def test_dry_run_writes_nothing(self) -> None:
        repo = self.make_repo("2026-06-01")
        queue = repo / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
        output = repo / "docs" / "codex" / "STATE_STATUS.md"

        result = cron.report(
            repo=repo,
            queue_path=queue,
            report_path=output,
            dry_run=True,
            today=dt.date(2026, 6, 10),
        )

        self.assertTrue(any(finding.code == "now_stale" for finding in result.findings))
        self.assertIsNone(result.gate)
        self.assertFalse(queue.exists())
        self.assertFalse(output.exists())

    def test_schedule_snippet_is_documentation_only(self) -> None:
        snippet = cron.schedule_snippet(Path("/tmp/fpai"))

        self.assertIn("Non-installed example", snippet)
        self.assertIn("tools/state_reconciler/cron.py --write-report", snippet)


if __name__ == "__main__":
    unittest.main()

