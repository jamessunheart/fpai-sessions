from __future__ import annotations

import unittest

from tools.agent_benchmark_intelligence import engine


class NorthStarMissionDocTest(unittest.TestCase):
    def test_north_star_doc_defines_required_targets(self) -> None:
        text = engine.DEFAULT_NORTH_STAR.read_text(encoding="utf-8")

        self.assertIn("outperform well-funded AI players", text)
        self.assertIn("capital and hardware efficiency", text)
        self.assertIn("without required external API calls", text)
        for target_id in engine.NORTH_STAR_TARGET_IDS:
            self.assertIn(target_id, text)

    def test_council_focus_cites_north_star_as_weight_directive(self) -> None:
        focus = (engine.REPO_ROOT / "core" / "STATE" / "COUNCIL_FOCUS.md").read_text(encoding="utf-8")

        self.assertIn("core/STATE/NORTH_STAR.md", focus)
        self.assertIn("Primary weight directive", focus)
        self.assertIn("unified memory directive", focus)
        self.assertIn("Council JSON should cite `NORTH_STAR.md`", focus)

    def test_d057_report_maps_to_north_star_targets(self) -> None:
        report = engine.build_report(
            external_findings=engine.load_external_findings(),
            internal_evidence=[],
            now="2026-06-17T00:00:00Z",
        )

        north_star = report["north_star"]
        self.assertEqual(north_star["status"], "loaded")
        self.assertEqual(north_star["source"], "core/STATE/NORTH_STAR.md")
        self.assertEqual(north_star["target_ids"], list(engine.NORTH_STAR_TARGET_IDS))
        self.assertIn("d057 Agent Benchmarking Intelligence", north_star["proof_path"])
        for target_id in engine.NORTH_STAR_TARGET_IDS:
            self.assertIn(target_id, north_star["criteria"])
        self.assertIn("without required external API calls", north_star["criteria"]["sovereign_run"])
        self.assertIn("open-model capable", north_star["criteria"]["sovereign_run"])
        self.assertIn("operator-controlled", north_star["criteria"]["sovereign_run"])


if __name__ == "__main__":
    unittest.main()
