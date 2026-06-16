#!/usr/bin/env python3
"""Regression checks for the locked Lantern-Mirror-Ledger principle."""
from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PRINCIPLE_PATH = REPO_ROOT / "docs" / "codex" / "LANTERN_MIRROR_LEDGER_PRINCIPLE.md"


class LanternMirrorLedgerPrincipleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PRINCIPLE_PATH.read_text(encoding="utf-8")

    def test_principle_locks_the_three_part_architecture(self) -> None:
        required = (
            "Status: locked by answered decision d058.",
            "Lantern -> Mirror -> shared scoring ledger -> advisory role placement",
            "Lantern scans external AI benchmarking",
            "Mirror applies those signals inward",
            "Both feed one shared scoring ledger",
            "not a one-off d057 implementation detail",
        )
        for needle in required:
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_required_role_boundaries_are_present(self) -> None:
        role_terms = (
            "**Lantern:** look outward.",
            "fixed-source public benchmark/eval",
            "untrusted data",
            "**Mirror:** look inward.",
            "repo-local evidence",
            "**Shared scoring ledger:** make placement memory durable.",
            "one time-series record per agent/model evaluation row",
            "advisory until James/Ember approves",
        )
        for term in role_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.text)

    def test_non_negotiable_boundaries_cover_live_authority_risks(self) -> None:
        forbidden_auto_effects = (
            "change production routing authority",
            "train or fine-tune a model",
            "download or install models",
            "spend money",
            "deploy services",
            "send outreach",
            "grant an agent wider permissions",
        )
        for effect in forbidden_auto_effects:
            with self.subTest(effect=effect):
                self.assertIn(effect, self.text)

    def test_repo_anchors_exist(self) -> None:
        anchors = (
            "tools/agent_benchmark_intelligence/engine.py",
            "docs/codex/AGENT_BENCHMARK_INTELLIGENCE.md",
            "core/BUILD/signals/agent_benchmark_intelligence.json",
            "core/BUILD/signals/agent_scoring_ledger.jsonl",
            "core/BUILD/cron/fpai-agent-benchmark-intelligence.service",
            "core/BUILD/specs/SPEC_d057_agent-benchmarking-intelligence.md",
        )
        for anchor in anchors:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, self.text)
                self.assertTrue((REPO_ROOT / anchor).exists(), f"missing anchor: {anchor}")


if __name__ == "__main__":
    unittest.main()
