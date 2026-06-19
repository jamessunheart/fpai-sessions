from __future__ import annotations

import unittest
from pathlib import Path


class TelegramCorrectionWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Path(__file__).with_name("tgbot.py").read_text(encoding="utf-8")

    def test_context_injection_is_called_with_conversation_id(self) -> None:
        self.assertIn("build_context_system_suffix(", self.source)
        self.assertIn("conversation_id=conversation_id", self.source)
        self.assertIn('include_system_state=blocks["system_state"]', self.source)
        self.assertIn("_synthesize_answer(", self.source)
        self.assertIn("context_route=context_route", self.source)

    def test_correction_capture_runs_before_inbound_log(self) -> None:
        capture_idx = self.source.index("capture_if_correction(conversation_id=str(chat_id), james_message=text)")
        log_idx = self.source.index('await _log_tg_message(str(chat_id), "user", text, update_id=update_id)')

        self.assertLess(capture_idx, log_idx)

    def test_becoming_capture_runs_before_inbound_log(self) -> None:
        capture_idx = self.source.index("capture_becoming_exchange(")
        log_idx = self.source.index('await _log_tg_message(str(chat_id), "user", text, update_id=update_id)')

        self.assertLess(capture_idx, log_idx)

    def test_attention_surfacing_receives_pgvector_hits(self) -> None:
        self.assertIn("attention_context_from_hits(", self.source)
        self.assertIn('"note_row_id": note_row_id', self.source)
        search_idx = self.source.index("ORDER BY embedding <=> %s::vector")
        attention_idx = self.source.index("attention_context_from_hits(")

        self.assertLess(search_idx, attention_idx)

    def test_context_routing_gate_controls_brain_search(self) -> None:
        self.assertIn('CURATOR_CONTEXT_ROUTING', self.source)
        self.assertIn("context_route = _classify_context_route(text)", self.source)
        self.assertIn('hits = await _search_brain(text) if blocks["brain_search"] else []', self.source)


if __name__ == "__main__":
    unittest.main()
