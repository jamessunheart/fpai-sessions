#!/usr/bin/env python3
"""Static contract tests for the server build-loop pytest gate."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class PytestGateShellContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_pytest_gate_runs_before_independent_review(self) -> None:
        gate = self.text.index("tools/build_loop/test_gate.py")
        review = self.text.index("# review ($0 claude -p, PROTECTED_PATHS aware)")
        self.assertLess(gate, review)
        self.assertIn('PYTEST_GATE_TIMEOUT="${PYTEST_GATE_TIMEOUT:-180}"', self.text)
        self.assertIn('--python "$PY"', self.text)
        self.assertIn('--timeout "$PYTEST_GATE_TIMEOUT"', self.text)

    def test_failed_pytest_gate_surfaces_changes_without_merge(self) -> None:
        gate_start = self.text.index("tools/build_loop/test_gate.py")
        gate_end = self.text.index("# review ($0 claude -p, PROTECTED_PATHS aware)")
        gate_block = self.text[gate_start:gate_end]
        self.assertIn('dec set-build-result "$DID" "$BR" "changes"', gate_block)
        self.assertIn("PYTEST GATE FAILED", gate_block)
        self.assertIn("pytest-gate-failed", gate_block)
        self.assertIn("return 0", gate_block)

    def test_passed_pytest_gate_report_is_committed_for_quality_score(self) -> None:
        self.assertIn('TEST_GATE_REPORT="$WT/core/BUILD/reports/${SPECID}.test_gate.json"', self.text)
        self.assertIn("record pytest gate pass", self.text)
        self.assertIn("pytest-gate-passed", self.text)


if __name__ == "__main__":
    unittest.main()
