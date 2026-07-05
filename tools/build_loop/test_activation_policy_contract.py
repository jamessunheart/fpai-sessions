#!/usr/bin/env python3
"""Static contract tests for activate-or-declare-inert build policy."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class ActivationPolicyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_generated_spec_includes_activation_policy(self) -> None:
        self.assertIn("Activation policy:", self.text)
        self.assertIn("core/BUILD/activate/${SPECID}.sh", self.text)
        self.assertIn("build_kind=library or build_kind=inert", self.text)

    def test_policy_check_runs_before_independent_review(self) -> None:
        policy = self.text.index("tools/build_loop/activation_policy.py")
        review = self.text.index("# review ($0 claude -p, PROTECTED_PATHS aware)")
        self.assertLess(policy, review)
        self.assertIn("activation-policy-failed", self.text)
        self.assertIn("missing activation policy declaration", self.text)


if __name__ == "__main__":
    unittest.main()
