from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.loop import direct


class DirectLoopTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-loop-direct-"))

    def write_buildstream(self, root: Path, body: str) -> Path:
        path = root / "INTENT_BUILDSTREAM.md"
        path.write_text("# Intent Buildstream\n\n" + body, encoding="utf-8")
        return path

    def test_tick_runs_ready_intents_by_weight_and_gates_reserved_step(self) -> None:
        root = self.root()
        queue = root / "queue.json"
        log = root / "direct.jsonl"
        memory = root / "memory.json"
        handoff = root / "HANDOFF.md"
        buildstream = self.write_buildstream(
            root,
            "- Low | id: low | status: ready | weight: 10 | next: draft low note | stream: Game\n"
            "- Reserved | id: reserved | status: ready | weight: 90 | next: draft prep; send public post | stream: Ventures\n"
            "- Delegable | id: delegable | status: ready | weight: 80 | next: draft implementation brief | stream: Game\n"
            "- Blocked | id: blocked | status: blocked | weight: 999 | next: send blocked thing | stream: Game\n",
        )

        summary = direct.tick(
            buildstream_path=buildstream,
            queue_path=queue,
            log_path=log,
            memory_path=memory,
            handoff_path=handoff,
            max_intents=2,
        )

        self.assertEqual([outcome.intent_id for outcome in summary.outcomes], ["reserved", "delegable"])
        self.assertEqual(summary.intents_touched, 2)
        self.assertEqual(summary.steps_executed, 2)
        self.assertEqual(summary.gates_raised, 1)
        self.assertEqual(summary.outcomes[0].status, "gated")
        self.assertEqual(summary.outcomes[0].first_gate, "send public post")
        self.assertEqual(summary.outcomes[1].status, "completed")

        queue_data = json.loads(queue.read_text(encoding="utf-8"))
        self.assertEqual(len(queue_data["gates"]), 1)
        self.assertIn("send public post", queue_data["gates"][0]["question"])
        saved = json.loads(log.read_text(encoding="utf-8").strip())
        self.assertEqual(saved["intents_touched"], 2)
        self.assertIn("Self-directing loop tick", handoff.read_text(encoding="utf-8"))

    def test_dry_run_writes_nothing(self) -> None:
        root = self.root()
        queue = root / "queue.json"
        log = root / "direct.jsonl"
        memory = root / "memory.json"
        handoff = root / "HANDOFF.md"
        buildstream = self.write_buildstream(
            root,
            "- Reserved | id: reserved | status: ready | weight: 90 | next: draft prep; approve final choice | stream: Game\n",
        )

        summary = direct.tick(
            dry_run=True,
            buildstream_path=buildstream,
            queue_path=queue,
            log_path=log,
            memory_path=memory,
            handoff_path=handoff,
            max_intents=1,
        )

        self.assertEqual(summary.gates_raised, 1)
        self.assertFalse(queue.exists())
        self.assertFalse(log.exists())
        self.assertFalse(memory.exists())
        self.assertFalse(handoff.exists())

    def test_memory_skips_intent_blocked_on_open_gate_next_tick(self) -> None:
        root = self.root()
        queue = root / "queue.json"
        log = root / "direct.jsonl"
        memory = root / "memory.json"
        handoff = root / "HANDOFF.md"
        buildstream = self.write_buildstream(
            root,
            "- Top | id: top | status: ready | weight: 90 | next: draft prep; send public post | stream: Ventures\n"
            "- Next | id: next | status: ready | weight: 80 | next: draft implementation brief | stream: Game\n",
        )

        first = direct.tick(
            buildstream_path=buildstream,
            queue_path=queue,
            log_path=log,
            memory_path=memory,
            handoff_path=handoff,
            max_intents=1,
        )
        second = direct.tick(
            buildstream_path=buildstream,
            queue_path=queue,
            log_path=log,
            memory_path=memory,
            handoff_path=handoff,
            max_intents=1,
        )

        self.assertEqual([outcome.intent_id for outcome in first.outcomes], ["top"])
        self.assertEqual(first.gates_raised, 1)
        self.assertEqual(second.skipped_intents, ["top"])
        self.assertEqual([outcome.intent_id for outcome in second.outcomes], ["next"])
        self.assertEqual(second.gates_raised, 0)

        memory_data = json.loads(memory.read_text(encoding="utf-8"))
        self.assertEqual(memory_data["intents"]["top"]["status"], "gated")
        self.assertEqual(memory_data["intents"]["next"]["status"], "completed")
        queue_data = json.loads(queue.read_text(encoding="utf-8"))
        self.assertEqual(len(queue_data["gates"]), 1)

    def test_no_ready_intents_records_empty_summary(self) -> None:
        root = self.root()
        log = root / "direct.jsonl"
        memory = root / "memory.json"
        handoff = root / "HANDOFF.md"
        buildstream = self.write_buildstream(
            root,
            "- Waiting | id: waiting | status: blocked | weight: 90 | next: draft later | stream: Game\n",
        )

        summary = direct.tick(buildstream_path=buildstream, log_path=log, memory_path=memory, handoff_path=handoff)

        self.assertEqual(summary.intents_touched, 0)
        self.assertEqual(summary.steps_executed, 0)
        self.assertEqual(summary.gates_raised, 0)
        self.assertTrue(memory.exists())
        self.assertIn("no READY intents found", handoff.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
