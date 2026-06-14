from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.apprentice import select


class ApprenticeSelectTest(unittest.TestCase):
    def write_buildstream(self, body: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-apprentice-select-"))
        path = root / "INTENT_BUILDSTREAM.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_loads_and_selects_highest_ready_intent(self) -> None:
        path = self.write_buildstream(
            "- Lower | id: low | status: ready | weight: 10 | next: draft a note | stream: Game\n"
            "- Higher | id: high | status: ready | weight: 90 | next: draft a brief | stream: Ventures\n"
            "- Blocked | id: blocked | status: blocked | weight: 200 | next: draft later | stream: Game\n"
        )

        intent = select.select_intent(select.load_intents(path))

        self.assertEqual(intent["id"], "high")
        self.assertEqual(intent["weight"], 90)

    def test_selects_explicit_id(self) -> None:
        path = self.write_buildstream(
            "- One | id: one | status: ready | weight: 90 | next: draft one | stream: Game\n"
            "- Two | id: two | status: ready | weight: 10 | next: draft two | stream: Game\n"
        )

        intent = select.select_intent(select.load_intents(path), "two")

        self.assertEqual(intent["id"], "two")

    def test_dry_run_selector_writes_nothing_and_names_bottleneck(self) -> None:
        path = self.write_buildstream(
            "- Bottleneck Session | id: results-bottleneck-session | results: revenue | status: ready | "
            "weight: 90 | tier: human | next: Name 3-5 warm leads for the founding $250 Bottleneck offer | "
            "verbs: name leads, draft cold list, checkpoint | stream: Ventures\n"
        )
        intent = select.select_intent(select.load_intents(path))
        normalized = select.normalize_for_apprentice(intent)
        result = select.dry_run_intent(intent)
        payload = select.selector_payload(normalized, result)

        self.assertEqual(payload["selected_intent"]["id"], "results-bottleneck-session")
        self.assertEqual(payload["apprentice_dry_run"]["status"], "gated")
        self.assertEqual(payload["would_do"][0]["step"], "draft candidate leads")
        self.assertEqual(payload["would_pause_at"]["step"], "approve and send these 5")
        self.assertIn("pauses only", payload["why"])
        self.assertFalse((path.parent / "queue.json").exists())

    def test_selector_main_writes_ledger_only_when_requested(self) -> None:
        path = self.write_buildstream(
            "- Bottleneck Session | id: results-bottleneck-session | status: ready | "
            "weight: 90 | tier: human | next: Name 3-5 warm leads | "
            "verbs: name leads, draft cold list, checkpoint | stream: Ventures\n"
        )
        ledger = path.parent / "ledger.jsonl"

        with mock.patch("sys.stdout"):
            select.main(["--buildstream", str(path), "--json"])
        self.assertFalse(ledger.exists())

        with mock.patch("sys.stdout"):
            select.main(["--buildstream", str(path), "--ledger", str(ledger), "--json"])
        self.assertTrue(ledger.exists())

    def test_no_ready_intents_fails_closed(self) -> None:
        path = self.write_buildstream(
            "- Waiting | id: waiting | status: blocked | weight: 90 | next: draft later | stream: Game\n"
        )

        with self.assertRaises(ValueError):
            select.select_intent(select.load_intents(path))


if __name__ == "__main__":
    unittest.main()
