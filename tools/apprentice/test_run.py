from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.apprentice.run import run_intent


class ApprenticeRunTest(unittest.TestCase):
    def make_tmp(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-apprentice-test-"))

    def test_delegable_only_intent_completes_without_gate(self) -> None:
        root = self.make_tmp()
        result = run_intent(
            {
                "id": "draft-brief",
                "stream": "Game",
                "next": "draft a short implementation brief; summarize the test plan",
            },
            log_path=root / "runs.jsonl",
        )

        self.assertEqual(result.status, "completed")
        self.assertFalse(result.gated)
        self.assertEqual(len(result.steps), 2)
        self.assertTrue(all(not step.reserved for step in result.steps))
        self.assertTrue((root / "runs.jsonl").exists())

    def test_reserved_step_writes_one_gate_and_pauses(self) -> None:
        root = self.make_tmp()
        queue = root / "queue.json"
        result = run_intent(
            {
                "id": "lead-flow",
                "stream": "Ventures",
                "next": "draft a warm lead list; send the outreach email",
            },
            queue_path=queue,
            log_path=root / "runs.jsonl",
            handoff_path=root / "HANDOFF.md",
        )

        self.assertEqual(result.status, "gated")
        self.assertTrue(result.gated)
        self.assertEqual(len(result.steps), 2)
        self.assertFalse(result.steps[0].reserved)
        self.assertTrue(result.steps[1].reserved)
        self.assertEqual(result.steps[1].action, "gate")
        self.assertIsNotNone(result.steps[1].gate)
        gate = result.steps[1].gate or {}
        self.assertEqual(gate["state"], "open")
        self.assertEqual(gate["stream"], "Ventures")
        self.assertIn("send the outreach email", gate["question"])

        data = json.loads(queue.read_text(encoding="utf-8"))
        self.assertEqual(len(data["gates"]), 1)
        self.assertEqual(data["gates"][0]["id"], gate["id"])
        self.assertTrue((root / "runs.jsonl").exists())
        handoff = (root / "HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("Apprentice run", handoff)
        self.assertIn("draft a warm lead list", handoff)
        self.assertIn("send the outreach email", handoff)

    def test_dry_run_writes_nothing(self) -> None:
        root = self.make_tmp()
        queue = root / "queue.json"
        log = root / "runs.jsonl"
        result = run_intent(
            {
                "id": "dry-run-gate",
                "stream": "Game",
                "next": "summarize the candidate; approve and publish the final post",
            },
            dry_run=True,
            queue_path=queue,
            log_path=log,
            handoff_path=root / "HANDOFF.md",
        )

        self.assertEqual(result.status, "gated")
        self.assertTrue(result.gated)
        self.assertFalse(queue.exists())
        self.assertFalse(log.exists())
        self.assertFalse((root / "HANDOFF.md").exists())


if __name__ == "__main__":
    unittest.main()
