#!/usr/bin/env python3
"""Static contract tests for mandatory live-service activation smoke guard."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "build_loop" / "server_build_loop.sh"
GUARD = ROOT / "tools" / "build_loop" / "live_service_guard.py"


class LiveDeployGuardContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.guard = GUARD.read_text(encoding="utf-8")

    def test_activation_scripts_run_through_guard_not_direct_bash(self) -> None:
        self.assertIn("live_service_guard.py", self.script)
        self.assertIn("--activate-script \"$ACTIVATE_SCRIPT\"", self.script)
        self.assertIn("--base-ref \"$PRE_SHA\"", self.script)
        self.assertIn("--head-ref \"$HEAD_SHA\"", self.script)
        self.assertNotIn('bash "$ACTIVATE_SCRIPT" 2>&1 | head', self.script)

    def test_failed_post_deploy_smoke_reverts_repo_acceptance(self) -> None:
        guard_call = self.script.index("live_service_guard.py")
        reset = self.script.index('git -C "$REPO" reset --hard "$PRE_SHA"', guard_call)
        held = self.script.index('dec set-build-result "$DID" "$BR" "changes"', reset)
        self.assertLess(guard_call, reset)
        self.assertLess(reset, held)
        self.assertIn("post-deploy smoke failed; auto-reverted", self.script)

    def test_guard_carries_live_service_map_backup_smoke_and_alert(self) -> None:
        self.assertIn("TARGETS", self.guard)
        self.assertIn("sunheart-brain-tgbot", self.guard)
        self.assertIn("create_backup", self.guard)
        self.assertIn("restore_backup", self.guard)
        self.assertIn("smoke_bot", self.guard)
        self.assertIn("journalctl", self.guard)
        self.assertIn("systemctl", self.guard)
        self.assertIn("deploy failed smoke-test, auto-reverted", self.guard)


if __name__ == "__main__":
    unittest.main()
