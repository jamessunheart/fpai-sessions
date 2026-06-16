from __future__ import annotations

import unittest
from pathlib import Path


class TelegramUserAgentWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Path(__file__).with_name("tgbot.py").read_text(encoding="utf-8")

    def test_tenant_branch_logs_to_thread_not_capture_buffer(self) -> None:
        tenant_branch = self.source.split("if not is_owner:", 1)[1].split(
            "# james_ask inbound DISABLED", 1
        )[0]

        self.assertIn('await _log_user_thread(user_id, "user", text)', tenant_branch)
        self.assertIn('await _log_user_thread(user_id, "bot", answer_body)', tenant_branch)
        self.assertNotIn("await _log_tg_message(user_id", tenant_branch)

    def test_public_fallback_onboarding_requires_explicit_env_flag(self) -> None:
        self.assertIn("MULTIUSER_OPEN_ONBOARDING", self.source)
        self.assertIn('return ""', self.source)


if __name__ == "__main__":
    unittest.main()
