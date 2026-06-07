from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tools.selftest import check, report


class SelftestReportTestCase(unittest.TestCase):
    def sample_checks(self) -> list[check.Check]:
        return [
            check.Check("router", check.PASS, "dry-run ok", "routes one step"),
            check.Check("git isolation", check.WARN, "dirty paths=2", "know committed vs local"),
        ]

    def test_verdict_warn_if_any_warning(self) -> None:
        self.assertEqual(report.verdict(self.sample_checks()), check.WARN)

    def test_verdict_fail_if_any_failure(self) -> None:
        checks = self.sample_checks() + [check.Check("proof", check.FAIL, "missing", "return loop")]
        self.assertEqual(report.verdict(checks), check.FAIL)

    def test_render_markdown_contains_verdict_and_checks(self) -> None:
        rendered = report.render_markdown(
            self.sample_checks(),
            dt.datetime(2026, 6, 6, 18, 0, tzinfo=dt.timezone.utc),
        )

        self.assertIn("# Self-Standing One-Day Test Report", rendered)
        self.assertIn("## Verdict: WARN", rendered)
        self.assertIn("| PASS | router | dry-run ok | routes one step |", rendered)

    def test_write_report(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-selftest-report-"))
        target = root / "docs" / "codex" / "SELF_STANDING_TEST_REPORT.md"

        report.write_report(target, "# report\n")

        self.assertEqual(target.read_text(encoding="utf-8"), "# report\n")


if __name__ == "__main__":
    unittest.main()
