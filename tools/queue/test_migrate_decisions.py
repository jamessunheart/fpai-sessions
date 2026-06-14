from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.queue import build
from tools.queue import migrate_decisions


class MigrateDecisionsTestCase(unittest.TestCase):
    def test_parse_and_migrate_live_open_decisions(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-migrate-decisions-"))
        decisions = root / "DECISIONS.md"
        queue = root / "HUMAN_EDGE_QUEUE.json"
        decisions.write_text(
            "# DECISIONS\n\n"
            "## 🟡 Open — your call\n\n"
            '- 🔴 **Run the dispatched builds** — 3 builds queued.\n'
            '  ↳ answer: say "running them" / "after X" / "checkpoint"\n\n'
            "- 🟡 **Camp Zen first-cohort offer shape** — blocks booking page.\n"
            "  ↳ answer: pick the shape → Ember drafts the offer page\n\n"
            "## 👀 Watching\n\n- no action\n",
            encoding="utf-8",
        )

        migrated = migrate_decisions.migrate(decisions, queue, render_decisions=True)

        data = build.load_queue(queue)
        self.assertEqual(len(migrated), 2)
        self.assertEqual(len(data["gates"]), 2)
        self.assertTrue(data["gates"][0]["urgent"])
        self.assertEqual(data["gates"][1]["stream"], "Zen")
        self.assertEqual(data["gates"][1]["verbs"], ["pick the shape", "checkpoint"])
        rendered = decisions.read_text(encoding="utf-8")
        self.assertIn("Rendered from `core/STATE/HUMAN_EDGE_QUEUE.json`", rendered)
        self.assertIn("## 👀 Watching", rendered)

        rerun = migrate_decisions.parse_open_decisions(rendered)

        self.assertEqual(len(rerun), 2)
        self.assertEqual(rerun[0]["verbs"], ["running them", "after X", "checkpoint"])


if __name__ == "__main__":
    unittest.main()
