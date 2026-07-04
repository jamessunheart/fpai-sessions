import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


DAY0 = {
    "physical": [6, 5],
    "mental": [7, 4],
    "spiritual": [8, 7],
    "social": [5, 4],
    "emotional": [6, 6],
    "financial": [4, 5],
    "environmental": [8, 8],
}


def load_champion_module(tmp: str):
    os.environ["CHAMPION_DATA_DIR"] = str(Path(tmp) / "champions")
    os.environ["PROOFS_DATA_DIR"] = str(Path(tmp) / "proofs")
    os.environ["CARDS_DATA_DIR"] = str(Path(tmp) / "cards")
    os.environ["LEADS_DATA_DIR"] = str(Path(tmp) / "leads")
    os.environ["MIRRORS_DATA_DIR"] = str(Path(tmp) / "mirrors")
    os.environ["TIERS_DATA_DIR"] = str(Path(tmp) / "tiers")
    os.environ["RETREAT_DATA_DIR"] = str(Path(tmp) / "retreat")
    os.environ["GOALS_DATA_DIR"] = str(Path(tmp) / "goals")
    os.environ["CREDITS_DATA_DIR"] = str(Path(tmp) / "credits")
    os.environ["STORE_DATA_DIR"] = str(Path(tmp) / "store")
    os.environ["FPAI_REPO_ROOT"] = str(Path(__file__).resolve().parents[3])
    module_path = Path(__file__).resolve().parents[3] / "SERVICES/champion-sign/main.py"
    spec = importlib.util.spec_from_file_location("champion_sign_life_test", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ChampionLifeLeadTests(unittest.TestCase):
    def test_scores_life_lead_with_existing_score_life_math(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            req = SimpleNamespace(
                name="Lia",
                email="lia@example.test",
                phone=None,
                timezone=None,
                preferred_contact=None,
                interest="life-assessment",
                lens="life",
                bottleneck="I want a clearer aim and steadier daily practice.",
                seven_areas=None,
                life_answers=DAY0,
                life_context={"spiritual": "Build the village that shows paradise is practical."},
            )
            result, deliverable = mod._score_life_lead(req)
            md = mod._render_lead_md(req, "2026-07-04", life_result=result, life_deliverable=deliverable)

        self.assertEqual(result["allocation_score"], 59.3)
        self.assertEqual(result["practice_target"], "social")
        self.assertIn("Life lens Allocation Score", md)
        self.assertIn("life_allocation_score: 59.3", md)
        self.assertIn("Your named AIM", md)


if __name__ == "__main__":
    unittest.main()
