#!/usr/bin/env python3
"""Static contract tests for server_build_loop.sh auto-merge governance."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class AutoMergeGovernanceShellContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_auto_merge_path_requires_independent_review_approve(self):
        self.assertIn("# AUTO-MERGE only independent-review APPROVE builds.", self.text)
        self.assertIn('if [ "$RC" = 0 ]; then', self.text)
        self.assertNotIn('if [ "$RC" != 2 ]; then', self.text)

    def test_still_flagged_review_is_held_for_manual_review(self):
        self.assertIn("AI review still flagged this build after revision attempts", self.text)
        self.assertIn("_ev=review-held", self.text)
        self.assertIn("Ember/James: review flagged $DID", self.text)
        self.assertIn("revision held-for-review", self.text)
        self.assertNotIn("auto-merged-flagged", self.text)
        self.assertNotIn("fallback-auto-merge", self.text)

    def test_approved_merge_conflicts_still_surface_as_conflicts(self):
        pattern = re.compile(
            r'elif \[ "\$RC" = 0 \]; then\s+'
            r'_tail="[^"]*Real merge conflict[^"]*"; _ev=conflict;',
            re.S,
        )
        self.assertRegex(self.text, pattern)


if __name__ == "__main__":
    unittest.main()
