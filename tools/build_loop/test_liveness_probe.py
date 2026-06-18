#!/usr/bin/env python3
"""Static contract tests for server_build_loop.sh post-merge liveness probes."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"
DECISIONS = ROOT / "SERVICES" / "sunheart-brain" / "curator" / "decisions.py"


class LivenessProbeShellContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")
        cls.decisions = DECISIONS.read_text(encoding="utf-8")

    def test_pending_builds_carries_liveness_check_from_decision_json(self):
        self.assertIn("liveness TEXT", self.decisions)
        self.assertIn("liveness_check", self.decisions)
        self.assertIn("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS liveness_check TEXT", self.decisions)
        self.assertIn("ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS liveness TEXT", self.decisions)
        self.assertIn("proof_expected, liveness", self.decisions)
        self.assertIn("LIVENESS_DECLARATION=$(printf", self.text)
        self.assertIn('.get("liveness") or ""', self.text)
        self.assertIn("LIVENESS_CHECK=$(printf", self.text)
        self.assertIn('.get("liveness_check") or ""', self.text)

    def test_probe_runs_after_activation_and_before_merge_notification(self):
        activation = self.text.index('python3 "$REPO/tools/build_loop/ops_log.py" merge activated')
        probe = self.text.index('run_liveness_probe "$LIVENESS_DECLARATION" "$LIVENESS_CHECK"')
        approved_notice = self.text.index('tg "$V · AUTO-MERGED')
        self.assertLess(activation, probe)
        self.assertLess(probe, approved_notice)

    def test_probe_has_kill_switch_timeout_and_ops_events(self):
        self.assertIn("LIVENESS_PROBE_DISABLE", self.text)
        self.assertIn("tools.liveness.probe", self.text)
        self.assertIn("--declaration", self.text)
        self.assertIn("--legacy-command", self.text)
        self.assertIn('"liveness:fail"', self.text)

    def test_failure_queues_followup_spec(self):
        self.assertIn("queue_liveness_followup", self.text)
        self.assertIn('"Liveness failed after auto-merge for {specid}"', self.text)
        self.assertIn("dec seed", self.text)
        self.assertRegex(self.text, re.compile(r'ops_log\.py" liveness "liveness:fail".*queue_liveness_followup', re.S))

    def test_probe_runs_with_typed_declaration_and_legacy_fallback(self):
        self.assertIn('run_liveness_probe "$LIVENESS_DECLARATION" "$LIVENESS_CHECK"', self.text)
        self.assertIn('--spec-file "$spec_file"', self.text)


if __name__ == "__main__":
    unittest.main()
