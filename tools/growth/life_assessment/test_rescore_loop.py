import tempfile
import unittest
from pathlib import Path

from tools.growth.life_assessment import rescore_loop


DAY0 = {
    "physical": [6, 5],
    "mental": [7, 4],
    "spiritual": [8, 7],
    "social": [5, 4],
    "emotional": [6, 6],
    "financial": [4, 5],
    "environmental": [8, 8],
    "context": {"spiritual": "Build the village that shows paradise is practical."},
}

DAY14 = {
    "physical": [7, 6],
    "mental": [7, 6],
    "spiritual": [8, 8],
    "social": [7, 6],
    "emotional": [7, 7],
    "financial": [5, 6],
    "environmental": [8, 8],
}


class LifeRescoreLoopTests(unittest.TestCase):
    def test_checkin_applies_one_bounded_area_nudge_per_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            answers = {k: v for k, v in DAY0.items() if k != "context"}
            rescore_loop.start_participant("lia", answers, DAY0["context"], state_dir)

            first = rescore_loop.apply_checkin(
                "lia",
                "Had a clear supportive conversation with a friend and feel better.",
                when="2026-07-05",
                state_dir=state_dir,
            )
            second = rescore_loop.apply_checkin(
                "lia",
                "Another friend conversation today.",
                when="2026-07-05",
                state_dir=state_dir,
            )
            state = rescore_loop.load_participant("lia", state_dir)

        self.assertTrue(first["applied"])
        self.assertFalse(second["applied"])
        self.assertEqual(first["area"], "social")
        self.assertEqual(len(state["nudges"]), 1)
        self.assertEqual(state["running_areas"]["social"], 5.5)

    def test_cohort_report_exports_day0_to_day14_deltas(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            answers = {k: v for k, v in DAY0.items() if k != "context"}
            rescore_loop.start_participant("lia", answers, DAY0["context"], state_dir)
            rescore_loop.record_day14("lia", DAY14, {}, state_dir)
            report = rescore_loop.cohort_report(state_dir)
            csv_path = state_dir / "admin.csv"
            rescore_loop.write_csv(report, csv_path)
            csv_text = csv_path.read_text(encoding="utf-8")

        self.assertEqual(report["count"], 1)
        row = report["participants"][0]
        self.assertEqual(row["participant_id"], "lia")
        self.assertGreater(row["score_delta"], 0)
        self.assertGreater(row["area_deltas"]["social"], 0)
        self.assertIn("social_delta", csv_text)


if __name__ == "__main__":
    unittest.main()
