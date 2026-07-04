from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.growth import growth_allocator as ga


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class GrowthAllocatorTests(unittest.TestCase):
    def test_cycle_kills_breeds_distills_and_caps_allocation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = root / "assets.jsonl"
            out = root / "plan.json"
            patterns = root / "WINNING_PATTERNS.md"
            _write_rows(
                ledger,
                [
                    {
                        "asset_id": "ad-winner",
                        "type": "ad",
                        "status": "alive",
                        "generation": 0,
                        "genome": {
                            "frame": "savings",
                            "hook": "find hidden waste",
                            "audience": "owner_operator",
                            "format": "ad",
                            "channel": "meta",
                        },
                        "outcomes": {"impressions": 1200, "clicks": 72, "leads": 3, "audits": 1, "deals": 0},
                        "spend_usd": 9.0,
                    },
                    {
                        "asset_id": "ad-loser",
                        "type": "ad",
                        "status": "alive",
                        "genome": {"frame": "exec", "hook": "generic", "audience": "executive_team", "format": "ad", "channel": "meta"},
                        "outcomes": {"impressions": 1400, "clicks": 4, "leads": 0},
                        "spend_usd": 8.0,
                    },
                    {
                        "asset_id": "email-winner",
                        "type": "email",
                        "status": "alive",
                        "genome": {"frame": "partnership", "hook": "monday move", "audience": "assessment_lead", "format": "email", "channel": "email"},
                        "outcomes": {"impressions": 200, "clicks": 14, "leads": 1},
                    },
                ],
            )
            result = ga.run_cycle(
                ledger_path=ledger,
                output_path=out,
                patterns_path=patterns,
                ad_budget_usd=99,
                write=True,
            )
            final_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            pattern_text = patterns.read_text(encoding="utf-8")
            wrote_plan = out.exists()

        self.assertIn("ad-loser", result["killed"])
        self.assertIn("ad-winner", result["champions"])
        self.assertEqual(result["allocation_plan"]["ad_budget_usd"], 10.0)
        self.assertTrue(result["bred_children"])
        child = next(row for row in result["bred_children"] if row["parent_id"] == "ad-winner")
        self.assertEqual(child["parent_id"], "ad-winner")
        parent = next(row for row in final_rows if row["asset_id"] == "ad-winner")
        changed = [
            gene
            for gene, value in child["genome"].items()
            if value != parent["genome"].get(gene)
        ]
        self.assertEqual(changed, [child["mutated_gene"]])
        self.assertIn("ad-winner", pattern_text)
        self.assertTrue(wrote_plan)

    def test_article_floor_uses_assessment_starts_and_days_live(self) -> None:
        scored = ga.score_asset(
            {
                "asset_id": "article-old",
                "type": "article",
                "days_live": 45,
                "assessment_starts": 0,
                "outcomes": {"impressions": 300, "clicks": 20},
            }
        )
        kill, reason = ga.should_kill({"type": "article", "days_live": 45, "assessment_starts": 0}, scored)
        self.assertTrue(kill)
        self.assertIn("assessment start", reason)


if __name__ == "__main__":
    unittest.main()
