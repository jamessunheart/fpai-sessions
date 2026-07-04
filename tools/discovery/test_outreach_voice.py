from __future__ import annotations

import unittest

from tools.discovery import common
from tools.discovery import signals


class OutreachVoiceTests(unittest.TestCase):
    def test_outreach_voice_is_retired_historical_context(self):
        path = common.REPO_ROOT / "core" / "STATE" / "OUTREACH_VOICE.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("RETIRED", text)
        self.assertIn("Free Full Potential Assessment", text)
        self.assertIn("No manual/proactive outreach", text)

    def test_seeker_signals_is_non_empty_list_of_strings(self):
        self.assertIsInstance(signals.SEEKER_SIGNALS, list)
        self.assertGreater(len(signals.SEEKER_SIGNALS), 0)
        self.assertTrue(all(isinstance(item, str) and item for item in signals.SEEKER_SIGNALS))

    def test_historical_email_body_template_remains_marked_retired(self):
        path = common.REPO_ROOT / "core" / "STATE" / "OUTREACH_VOICE.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("The historical copy below must not be used for new sends.", text)
        self.assertIn("[first_name]", text)
        self.assertIn("[link]", text)

    def test_seeker_language_scores_above_generic_personal_growth(self):
        seeker_score = common.score_signal("I feel stuck and keep asking what's next for my full potential.")
        generic_score = common.score_signal("#personalgrowth tips and motivation")
        self.assertGreater(seeker_score, generic_score)


if __name__ == "__main__":
    unittest.main()
