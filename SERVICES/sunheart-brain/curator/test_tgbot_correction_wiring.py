from __future__ import annotations

import unittest
from pathlib import Path


class TelegramCorrectionWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Path(__file__).with_name("tgbot.py").read_text(encoding="utf-8")

    def test_context_injection_is_called_with_conversation_id(self) -> None:
        self.assertIn("build_context_system_suffix(conversation_id=conversation_id)", self.source)
        self.assertIn("_synthesize_answer(text, hits, conversation_id=str(chat_id))", self.source)

    def test_correction_capture_runs_before_inbound_log(self) -> None:
        capture_idx = self.source.index("capture_if_correction(conversation_id=str(chat_id), james_message=text)")
        log_idx = self.source.index('await _log_tg_message(str(chat_id), "user", text, update_id=update_id)')

        self.assertLess(capture_idx, log_idx)

    def test_becoming_capture_runs_before_inbound_log(self) -> None:
        capture_idx = self.source.index("capture_becoming_exchange(")
        log_idx = self.source.index('await _log_tg_message(str(chat_id), "user", text, update_id=update_id)')

        self.assertLess(capture_idx, log_idx)


if __name__ == "__main__":
    unittest.main()
