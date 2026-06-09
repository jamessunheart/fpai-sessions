from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.queue import build


class HumanEdgeQueueTestCase(unittest.TestCase):
    def queue_path(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-human-edge-"))
        return root / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"

    def test_add_gate_renders_queue_and_surfaces(self) -> None:
        path = self.queue_path()

        build.add_gate(
            gate_id="gate-1",
            surfaced="2026-06-09T12:00:00+00:00",
            stream="Zen",
            question="Approve Camp Zen founder camp price?",
            verbs=["approve", "revise", "checkpoint"],
            path=path,
        )

        data = build.load_queue(path)
        self.assertEqual(len(data["gates"]), 1)
        self.assertTrue(path.exists())
        self.assertTrue(path.with_suffix(".md").exists())
        self.assertIn("Approve Camp Zen founder camp price?", path.with_suffix(".md").read_text(encoding="utf-8"))
        self.assertIn("## 🟡 Open", build.render_decisions(data))
        self.assertIn("Options: `approve` / `revise` / `checkpoint`", build.render_home_decide(data))

    def test_answer_gate_flips_state_and_records_answer(self) -> None:
        path = self.queue_path()
        build.add_gate(
            gate_id="gate-2",
            surfaced="2026-06-09T12:00:00+00:00",
            stream="Game",
            question="Choose the next game loop?",
            verbs=["play", "hold"],
            path=path,
        )

        gate = build.answer_gate("gate-2", "hold", path)

        self.assertEqual(gate["state"], "answered")
        self.assertEqual(gate["answer"], "hold")
        self.assertEqual(build.open_gates(path), [])
        self.assertIn("## Answered", path.with_suffix(".md").read_text(encoding="utf-8"))

    def test_add_gate_dedups_by_id(self) -> None:
        path = self.queue_path()
        kwargs = {
            "gate_id": "same-id",
            "surfaced": "2026-06-09T12:00:00+00:00",
            "stream": "Play",
            "question": "Pick the play gate?",
            "verbs": ["yes", "no"],
            "path": path,
        }

        first = build.add_gate(**kwargs)
        second = build.add_gate(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(len(build.load_queue(path)["gates"]), 1)


if __name__ == "__main__":
    unittest.main()
