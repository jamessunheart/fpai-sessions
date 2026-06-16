from __future__ import annotations

import unittest
from pathlib import Path


class TelegramCorrectionWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Path(__file__).with_name("tgbot.py").read_text(encoding="utf-8")

    def test_context_injection_is_called_with_conversation_id(self) -> None:
        self.assertIn("build_context_system_suffix(conversation_id=conversation_id)", self.source)
        self.assertIn("conversation_id=str(chat_id)", self.source)
        self.assertIn("operator_context=is_owner", self.source)
        self.assertIn("_profile_context_system_prefix(user_id, operator_context=False)", self.source)

    def test_profile_user_path_does_not_search_james_brain(self) -> None:
        self.assertIn("actor_user_id = from_user or str(chat_id)", self.source)
        self.assertIn("is_profile_user = await _has_user_profile(actor_user_id)", self.source)
        self.assertIn("if not is_owner and not is_profile_user:", self.source)
        self.assertIn("hits = await _search_brain(text) if is_owner else []", self.source)
        self.assertIn("USER_CHAT_SYSTEM_PROMPT", self.source)
        self.assertIn("Do not claim access to James's private brain", self.source)
        self.assertIn('if text.startswith("/") and not is_owner:', self.source)
        self.assertIn('private_flag=not is_owner', self.source)

    def test_correction_capture_runs_before_inbound_log(self) -> None:
        owner_guard_idx = self.source.index("if is_owner:")
        capture_idx = self.source.index("capture_if_correction(conversation_id=str(chat_id), james_message=text)")
        log_idx = self.source.index(
            'await _log_tg_message(str(chat_id), "user", text, update_id=update_id, private_flag=not is_owner)'
        )

        self.assertLess(owner_guard_idx, capture_idx)
        self.assertLess(capture_idx, log_idx)


if __name__ == "__main__":
    unittest.main()
