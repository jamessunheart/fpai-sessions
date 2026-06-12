from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.results import engine


class ResultsEngineTestCase(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-results-engine-"))

    def write_buildstream(self, root: Path, body: str) -> Path:
        path = root / "INTENT_BUILDSTREAM.md"
        path.write_text("# Intent Buildstream\n\n" + body, encoding="utf-8")
        return path

    def test_picks_highest_weighted_ready_results_opportunity(self) -> None:
        root = self.root()
        buildstream = self.write_buildstream(
            root,
            "- id:low | weight:2 | status:ready | results:revenue | tier:ai | next:draft low offer | Low offer\n"
            "- id:top | weight:9 | status:ready | results:donation | tier:ai | next:draft donor ask | Donor ask\n"
            "- id:not-results | weight:99 | status:ready | route:auto | Internal maintenance\n",
        )

        result = engine.run_engine(
            buildstream_path=buildstream,
            results_lane_path=root / "RESULTS_LANE.md",
            queue_path=root / "HUMAN_EDGE_QUEUE.json",
            dry_run=True,
        )

        self.assertEqual(result.action, "ai-staged")
        self.assertIsNotNone(result.opportunity)
        self.assertEqual(result.opportunity.ident, "top")
        self.assertEqual(result.move, "draft donor ask")

    def test_ai_doable_move_lands_in_review_lane_not_queue(self) -> None:
        root = self.root()
        lane = root / "RESULTS_LANE.md"
        queue = root / "HUMAN_EDGE_QUEUE.json"
        buildstream = self.write_buildstream(
            root,
            "- id:intake | weight:6 | status:ready | results:revenue | tier:ai | next:draft Full Potential diagnostic intake | Revenue Front Door\n",
        )

        result = engine.run_engine(
            buildstream_path=buildstream,
            results_lane_path=lane,
            queue_path=queue,
            dry_run=False,
        )

        self.assertEqual(result.action, "ai-staged")
        self.assertTrue(lane.exists())
        text = lane.read_text(encoding="utf-8")
        self.assertIn("awaiting James review", text)
        self.assertIn("Nothing has been sent", text)
        self.assertFalse(queue.exists())

    def test_human_edge_move_writes_well_formed_gate(self) -> None:
        root = self.root()
        queue = root / "HUMAN_EDGE_QUEUE.json"
        buildstream = self.write_buildstream(
            root,
            "- id:send-lead | weight:7 | status:ready | results:enrollment | next:send to named lead | verbs:approve,revise,checkpoint | Lead send\n",
        )

        result = engine.run_engine(
            buildstream_path=buildstream,
            results_lane_path=root / "RESULTS_LANE.md",
            queue_path=queue,
            dry_run=False,
        )

        self.assertEqual(result.action, "human-gated")
        data = json.loads(queue.read_text(encoding="utf-8"))
        self.assertEqual(len(data["gates"]), 1)
        gate = data["gates"][0]
        self.assertEqual(gate["id"], "results-send-lead")
        self.assertEqual(gate["stream"], "Zen")
        self.assertEqual(gate["state"], "open")
        self.assertEqual(gate["verbs"], ["approve", "revise", "checkpoint"])
        self.assertIn("send to named lead", gate["question"])
        self.assertTrue(queue.with_suffix(".md").exists())

    def test_consequence_row_records_simulated_realized_result(self) -> None:
        root = self.root()
        ledger = root / "consequence.jsonl"

        row = engine.record_consequence(
            "intake",
            "signup",
            "test signup recorded",
            ledger,
        )

        self.assertTrue(row["realized"])
        saved = json.loads(ledger.read_text(encoding="utf-8").strip())
        self.assertEqual(saved["opportunity_id"], "intake")
        self.assertEqual(saved["outcome"], "signup")
        self.assertTrue(saved["realized"])


if __name__ == "__main__":
    unittest.main()

