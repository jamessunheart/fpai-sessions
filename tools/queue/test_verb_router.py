from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.queue import build, verb_router


class VerbRouterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-verb-"))
        self.queue = root / "HUMAN_EDGE_QUEUE.json"
        self.inbox = root / "messages.jsonl"
        self.cursor = root / "cursor.txt"
        self.log = root / "log.jsonl"
        build.add_gate(gate_id="g-stage", stream="Treasury", question="Stage idle cash?",
                       verbs=["stage it", "checkpoint"], path=self.queue)
        build.add_gate(gate_id="g-builds", stream="Game", question="Run builds?",
                       verbs=["running them", "checkpoint"], path=self.queue)

    def _msg(self, uid: int, text: str) -> str:
        return json.dumps({"update_id": uid, "type": "text", "text": text})

    def _route(self):
        return verb_router.route(self.queue, self.inbox, self.cursor, self.log)

    def test_unique_verb_answers_its_gate(self) -> None:
        self.inbox.write_text(self._msg(1, "Stage it") + "\n")
        actions = self._route()
        self.assertEqual(actions, [{**actions[0], "action": "answered",
                                    "gate": "g-stage", "verb": "stage it", "update_id": 1}])
        gate = [g for g in build.load_queue(self.queue)["gates"] if g["id"] == "g-stage"][0]
        self.assertEqual(gate["state"], "answered")

    def test_ambiguous_verb_is_never_guessed(self) -> None:
        self.inbox.write_text(self._msg(1, "checkpoint") + "\n")
        actions = self._route()
        self.assertEqual(actions[0]["action"], "ambiguous")
        self.assertEqual(set(actions[0]["gates"]), {"g-stage", "g-builds"})
        self.assertTrue(all(g["state"] == "open" for g in build.load_queue(self.queue)["gates"]))

    def test_conversation_text_is_ignored(self) -> None:
        self.inbox.write_text(self._msg(1, "hey can you stage it for me when convenient?") + "\n")
        self.assertEqual(self._route(), [])

    def test_cursor_prevents_double_answer(self) -> None:
        self.inbox.write_text(self._msg(1, "stage it") + "\n")
        self._route()
        self.inbox.write_text(self._msg(1, "stage it") + "\n" + self._msg(2, "hello") + "\n")
        self.assertEqual(self._route(), [])

    def test_log_written(self) -> None:
        self.inbox.write_text(self._msg(1, "running them") + "\n")
        self._route()
        logged = json.loads(self.log.read_text().splitlines()[0])
        self.assertEqual(logged["gate"], "g-builds")


if __name__ == "__main__":
    unittest.main()
