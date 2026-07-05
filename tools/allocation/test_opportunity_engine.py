import json
import tempfile
import unittest
from pathlib import Path

from tools.allocation import opportunity_engine as engine


class OpportunityEngineTest(unittest.TestCase):
    def test_seeded_portfolio_has_five_scored_opportunities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opportunities.json"

            portfolio = engine.ensure_seeded(path, now="2026-07-05T01:00:00Z")
            view = engine.ranked(portfolio)

            self.assertGreaterEqual(view["count"], 5)
            self.assertIn("Resource Optimization Audit", [row["title"] for row in view["all"]])
            self.assertTrue(all(row["opportunity_score"] is not None for row in view["all"]))
            self.assertTrue(all(row["allocation_score"] is not None for row in view["all"]))
            self.assertTrue(all(row["next_domino_score"] is not None for row in view["all"]))
            self.assertEqual(view["top_allocation"][0]["title"], "Resource Optimization Audit")
            self.assertEqual(view["next_domino"][0]["title"], "Opportunity Intelligence Engine")
            self.assertEqual(view["next_domino"][0]["topple_status"], "topple-ready")

    def test_missing_axes_keep_scores_blank(self) -> None:
        row = engine.score_row({"id": "blank", "title": "Blank", "axes": {"pain": 9}})

        self.assertIsNone(row["opportunity_score"])
        self.assertIsNone(row["allocation_score"])
        self.assertIsNone(row["cash_proximity_score"])
        self.assertIsNone(row["next_domino_score"])
        self.assertEqual(row["topple_status"], "human-edge")

    def test_missing_capability_blocks_topple_ready_status(self) -> None:
        row = engine.score_row(
            {
                "id": "healthcare",
                "title": "Healthcare",
                "axes": {
                    "pain": 10,
                    "market": 10,
                    "compounding": 10,
                    "difficulty": 1,
                    "time_to_revenue": 1,
                    "time_to_first_dollar": 1,
                    "path_to_recurring": 10,
                    "constraint": 10,
                    "leverage": 10,
                    "proof_speed": 10,
                    "topple_reversibility": 10,
                },
                "topple": {
                    "gate": "codex_build",
                    "next_action": "Build it",
                    "proof": "Proof",
                    "missing_capability": "regulated data sandbox",
                },
            }
        )

        self.assertIn("build capability first", row["topple_status"])
        self.assertIn("regulated data sandbox", row["topple_status"])

    def test_gap_scan_updates_matching_rows_without_fabricating_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opportunities.json"
            scan_path = Path(tmp) / "scans.jsonl"
            cap_path = Path(tmp) / "capability.jsonl"
            cap_path.write_text(
                json.dumps(
                    {
                        "event": "capability_created",
                        "title": "Voice call booking proof",
                        "reusable_intelligence": "AI phone receptionist can handle appointment calls.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = engine.run_gap_scan(
                path,
                scan_ledger=scan_path,
                capability_ledger=cap_path,
                web_urls=[],
                now="2026-07-05T02:00:00Z",
            )
            portfolio = engine.load_portfolio(path)
            row = next(item for item in portfolio["opportunities"] if item["id"] == "ai-voice-receptionist")

            self.assertEqual(result["signals_seen"], 1)
            self.assertEqual(result["opportunities_updated"], 1)
            self.assertEqual(row["questions"]["prove_quickly"], "")
            self.assertEqual(row["signals"][0]["source"], "capability_ledger")
            self.assertTrue(scan_path.exists())

    def test_format_and_digest_line_surface_rankings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opportunities.json"
            text = engine.format_portfolio(engine.ranked(engine.ensure_seeded(path)))
            line = engine.digest_line(path)

            self.assertIn("Top by Opportunity Score", text)
            self.assertIn("Do-now by Allocation Score", text)
            self.assertIn("Closest to Cash", text)
            self.assertIn("Next Domino", text)
            self.assertIn("Spot:", text)
            self.assertIn("Topple:", text)
            self.assertIn("Proof:", text)
            self.assertIn("opportunities: next-domino", line)

    def test_council_context_requires_allocation_portfolio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = engine.council_context(Path(tmp) / "opportunities.json")

            self.assertIn("OPPORTUNITY PORTFOLIO", text)
            self.assertIn("Next Domino Score", text)
            self.assertIn("Opportunity Intelligence Engine", text)
            self.assertIn("proof=", text)


if __name__ == "__main__":
    unittest.main()
