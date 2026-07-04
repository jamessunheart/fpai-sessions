from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "sites" / "fullpotential-com" / "index.html"
ACTIVATE = ROOT / "core" / "BUILD" / "activate" / "SPEC_d170_spec-d170-align-live-outbound-su.sh"


class FullPotentialHomeTests(unittest.TestCase):
    def test_homepage_above_fold_is_assessment_first(self) -> None:
        html = HOME.read_text(encoding="utf-8")
        hero = html.split("<!-- ============ CATEGORY STRIP ============ -->", 1)[0]
        self.assertIn("Start with your <em>Allocation Score</em>.", hero)
        self.assertIn('href="/assessment">Start the Free Assessment', hero)
        self.assertIn("Free assessment", hero)
        self.assertNotIn("What wants to <em>grow</em> today?", hero)
        self.assertNotIn('href="/game.html" title="The Full Potential Game">Game</a>', hero)

    def test_live_activation_script_names_required_surfaces(self) -> None:
        script = ACTIVATE.read_text(encoding="utf-8")
        self.assertIn("/opt/fpai/guide/guide_service.py", script)
        self.assertIn("/opt/fpai/leads/intake-agent.py", script)
        self.assertIn("fp-guide.service", script)
        self.assertIn("intake-agent.service", script)
        self.assertIn("Free Full Potential Assessment first", script)
        self.assertIn("Blueprint ($2,500)", script)


if __name__ == "__main__":
    unittest.main()
