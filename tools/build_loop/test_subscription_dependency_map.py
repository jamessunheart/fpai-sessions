#!/usr/bin/env python3
"""Regression checks for the subscription dependency map."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = REPO_ROOT / "docs" / "codex" / "SUBSCRIPTION_DEPENDENCY_MAP.md"


class SubscriptionDependencyMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = MAP_PATH.read_text(encoding="utf-8")

    def test_required_failure_sections_are_present(self) -> None:
        required = (
            "## Build Loop Step Map",
            "### Claude Max Pulled",
            "### ChatGPT Max Pulled",
            "### Both Pulled",
            "## Role Replacement Priority",
            "**Build Executor (P0):**",
            "**Independent Reviewer (P0):**",
        )
        for needle in required:
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_core_steps_cover_both_subscription_failures(self) -> None:
        rows = [
            line
            for line in self.text.splitlines()
            if line.startswith("| ") and "`" in line and not line.startswith("| Step ")
        ]
        self.assertGreaterEqual(len(rows), 10)
        for row in rows:
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            with self.subTest(step=cells[0]):
                self.assertGreaterEqual(len(cells), 6)
                self.assertTrue(cells[3], "missing Claude Max failure/degradation cell")
                self.assertTrue(cells[4], "missing ChatGPT Max failure/degradation cell")

    def test_referenced_evidence_paths_exist(self) -> None:
        paths = sorted(set(re.findall(r"`([^`]+)`", self.text)))
        evidence_paths = [
            path
            for path in paths
            if path.startswith(("tools/", "docs/", "core/", "curator/"))
            and "<" not in path
            and " " not in path
            and not path.endswith("/")
        ]
        self.assertGreaterEqual(len(evidence_paths), 12)
        for raw_path in evidence_paths:
            with self.subTest(path=raw_path):
                self.assertTrue((REPO_ROOT / raw_path).exists(), f"missing evidence path: {raw_path}")

    def test_known_subscription_call_sites_are_represented(self) -> None:
        call_sites = {
            "tools/build_loop/run_codex.sh": ("codex exec", "false \"result exists\" integration hazard"),
            "tools/autobuild/run.py": ("claude", "codex"),
            "tools/merge/ai_review.py": ("claude -p", "independent reviewer"),
            "tools/build_loop/self_audit.py": ("claude -p", "self-audit"),
            "tools/horizon/scanner.py": ("claude -p", "deterministic fallback"),
            "tools/beacon/seed_content_bank.py": ("claude -p", "fallback drafts"),
            "curator/blueprints/manager.py": ("claude -p --effort high", "blueprint"),
        }
        for raw_path, expected_map_terms in call_sites.items():
            source = (REPO_ROOT / raw_path).read_text(encoding="utf-8")
            with self.subTest(path=raw_path):
                self.assertIn(raw_path, self.text)
                for term in expected_map_terms:
                    self.assertIn(term, self.text)
                if "codex" in expected_map_terms:
                    self.assertIn("codex", source.lower())
                if "claude" in expected_map_terms[0]:
                    self.assertIn("claude", source.lower())


if __name__ == "__main__":
    unittest.main()
