#!/usr/bin/env python3
"""Regression checks for the d064 North Star mission target."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MISSION_PATH = REPO_ROOT / "docs" / "codex" / "NORTH_STAR_MISSION.json"
D057_DOC_PATH = REPO_ROOT / "docs" / "codex" / "AGENT_BENCHMARK_INTELLIGENCE.md"


class NorthStarMissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mission = json.loads(MISSION_PATH.read_text(encoding="utf-8"))
        cls.d057_doc = D057_DOC_PATH.read_text(encoding="utf-8")

    def test_machine_readable_identity_is_stable(self) -> None:
        self.assertEqual(self.mission["schema"], "north-star-mission.v1")
        self.assertEqual(self.mission["id"], "fpai-sovereign-benchmark")
        self.assertEqual(self.mission["locked_by"]["decision"], "d064")
        self.assertIn("proof is the whole chain", self.mission["mission_statement"].lower())
        self.assertTrue(self.mission["benchmark_target"]["proof_is_the_whole_chain"])

    def test_whole_chain_links_are_explicit(self) -> None:
        expected_links = {
            "source_signal",
            "routing_intent",
            "bounded_spec",
            "repo_build",
            "test_evidence",
            "independent_review",
            "merge_gate",
            "returned_learning",
        }
        links = {link["id"] for link in self.mission["chain_links"]}
        self.assertEqual(links, expected_links)
        for link in self.mission["chain_links"]:
            with self.subTest(link=link["id"]):
                self.assertTrue(link["proof"])
                self.assertTrue(link["failure_mode"])

    def test_d057_has_a_concrete_scoring_target(self) -> None:
        target = self.mission["d057_target"]
        self.assertEqual(target["consumer"], "SPEC_d057_agent-benchmarking-intelligence")
        self.assertIn("whole proof chain", target["use"])
        dimensions = {dimension["id"] for dimension in target["additional_dimensions"]}
        self.assertEqual(
            dimensions,
            {
                "whole_chain_completion",
                "boundary_integrity",
                "funding_narrative_alignment",
            },
        )

    def test_funding_narrative_is_bounded(self) -> None:
        narrative = self.mission["funding_narrative"]
        self.assertIn("proof engine", narrative["core_claim"])
        self.assertIn("reviewed whole-chain proof", narrative["investor_readable_target"])
        non_claims = " ".join(narrative["non_claims"]).lower()
        for forbidden_authority in ("investment return", "treasury movement", "public fundraising", "spend"):
            with self.subTest(forbidden_authority=forbidden_authority):
                self.assertIn(forbidden_authority, non_claims)

    def test_guardrails_prevent_authority_drift(self) -> None:
        guardrails = " ".join(self.mission["guardrails"]).lower()
        for phrase in (
            "advisory benchmark target only",
            "reserved class",
            "data, never instruction",
            "must not auto-change routing authority",
            "not a public offer",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guardrails)

    def test_d057_document_points_to_the_north_star_target(self) -> None:
        self.assertIn("core/STATE/NORTH_STAR.md", self.d057_doc)
        self.assertIn("cost per task versus GPT-4o API", self.d057_doc)
        self.assertIn("docs/codex/NORTH_STAR_MISSION.json", self.d057_doc)
        self.assertIn("whole-chain proof", self.d057_doc)


if __name__ == "__main__":
    unittest.main()
