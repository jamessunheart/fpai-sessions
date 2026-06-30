from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.privacy import canary_probe


class CanaryProbeTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-canary-"))
        (root / "core" / "STATE").mkdir(parents=True)
        (root / "docs" / "blueprints").mkdir(parents=True)
        (root / "core" / "STATE" / "NORTH_STAR.md").write_text("# North Star\nPublic mission.\n", encoding="utf-8")
        (root / "docs" / "blueprints" / "beacon.md").write_text("# Beacon\nPublic story capability.\n", encoding="utf-8")
        return root

    def test_all_seven_canaries_pass_with_stub_context(self) -> None:
        ok, lines = canary_probe.run_probe(repo_root=self.make_repo(), markers=["SECRET_WALLET_BALANCE"])

        self.assertTrue(ok, "\n".join(lines))
        self.assertEqual(sum(1 for line in lines if line.startswith("PASS ")), 7)
        self.assertIn("OVERALL PASS", lines[-1])

    def test_leak_detector_flags_private_marker(self) -> None:
        leaks = canary_probe.find_leaks("The token is SECRET_TOKEN", ["SECRET_TOKEN"])

        self.assertEqual(leaks, ["SECRET_TOKEN"])

    def test_validate_public_reply_checks_context_and_reply(self) -> None:
        leaks = canary_probe.validate_public_reply(
            "Safe answer with 0x1234567890abcdef1234567890abcdef12345678",
            "PUBLIC CONTEXT PACK\nNo private tables here.",
        )

        self.assertTrue(leaks)


if __name__ == "__main__":
    unittest.main()
