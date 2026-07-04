import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tools.leads import mail_leads


class MailLeadsAllocationScoreTests(unittest.TestCase):
    def test_allocation_audit_notification_appends_score(self):
        def fake_score(lead_base, lead_body):
            self.assertEqual(lead_base, "lead-1.md")
            self.assertIn("interest: allocation-audit", lead_body)
            return Path("/tmp/lead-1.allocation-score.md"), "# Allocation Score\n\nScore: 82/100"

        body = mail_leads.notification_body(
            "lead-1.md",
            "name: Ada\nemail: ada@example.test\ninterest: allocation-audit\n",
            "allocation-audit",
            score_runner=fake_score,
        )

        self.assertIn("Allocation Score generated: /tmp/lead-1.allocation-score.md", body)
        self.assertIn("# Allocation Score", body)
        self.assertIn("Reply to this email", body)

    def test_non_allocation_lead_does_not_score(self):
        score_runner = mock.Mock()
        body = mail_leads.notification_body(
            "lead-2.md",
            "name: Ben\ninterest: newsletter\n",
            "newsletter",
            score_runner=score_runner,
        )

        score_runner.assert_not_called()
        self.assertNotIn("Allocation Score", body)
        self.assertIn("Reply to this email", body)

    def test_life_assessment_notification_summarizes_stored_score(self):
        score_runner = mock.Mock()
        body = mail_leads.notification_body(
            "lead-life.md",
            "name: Lia\ninterest: life-assessment\nlife_allocation_score: 59.3\nlife_practice_target: social\n",
            "life-assessment",
            score_runner=score_runner,
        )

        score_runner.assert_not_called()
        self.assertIn("Life lens deliverable attached.", body)
        self.assertIn("Allocation Score: 59.3/100", body)
        self.assertIn("Practice target: social", body)

    def test_generate_allocation_score_calls_score_assessment_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "scores"

            def fake_runner(cmd, capture_output, text, timeout):
                self.assertIn("--lead", cmd)
                self.assertIn("--out", cmd)
                out = Path(cmd[cmd.index("--out") + 1])
                out.write_text("# Your Full Potential Assessment\n", encoding="utf-8")
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            with mock.patch.object(mail_leads, "DELIVERABLE_DIR", out_dir):
                out, text = mail_leads.generate_allocation_score("lead 3.md", "name: Cam\n", runner=fake_runner)

        self.assertEqual(out.name, "lead-3.md.allocation-score.md")
        self.assertIn("Full Potential Assessment", text)


if __name__ == "__main__":
    unittest.main()
