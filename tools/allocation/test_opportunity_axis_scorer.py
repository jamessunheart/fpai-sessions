import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.allocation import opportunity_axis_scorer as scorer
from tools.allocation import opportunity_engine as engine


AXES = {
    "pain": 8,
    "market": 7,
    "compounding": 9,
    "difficulty": 2,
    "time_to_revenue": 2,
    "time_to_first_dollar": 1,
    "path_to_recurring": 8,
    "constraint": 9,
    "leverage": 9,
    "proof_speed": 8,
    "topple_reversibility": 10,
}


class OpportunityAxisScorerTest(unittest.TestCase):
    def test_scores_unscored_rows_and_logs_advisory_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "opportunities.json"
            log_path = Path(tmp) / "axis_scores.jsonl"
            ledger.write_text(
                json.dumps(
                    {
                        "schema": "fpai_opportunity_portfolio_v1",
                        "opportunities": [
                            {
                                "id": "assessment-funnel-delivery-proof",
                                "title": "Assessment Funnel Delivery Proof",
                                "questions": {
                                    "problem": "Assessment captures leads but does not prove delivery.",
                                    "who_pays": "FPAI first.",
                                },
                                "axes": {},
                                "topple": {"gate": "ai_reversible"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                self.assertEqual(command[:2], ["claude", "-p"])
                self.assertIn("Required axes:", command[2])
                return subprocess.CompletedProcess(command, 0, json.dumps({"axes": AXES}), "")

            result = scorer.score_missing_axes(
                ledger,
                log_path=log_path,
                runner=fake_runner,
                now="2026-07-05T15:00:00Z",
            )

            self.assertEqual(result["scored"], 1)
            self.assertTrue(result["all_scores_present"])
            portfolio = engine.load_portfolio(ledger)
            row = portfolio["opportunities"][0]
            for axis in engine.REQUIRED_DOMINO_AXES:
                self.assertIsNotNone(row["axes"][axis])
            self.assertNotIn("opportunity_score", row)
            self.assertNotIn("next_domino_score", row)
            self.assertIsNotNone(engine.ranked(portfolio)["next_domino"][0]["next_domino_score"])
            self.assertEqual(row["axis_score_basis"]["source"], "claude_advisory_axis_scorer")
            logs = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(logs[0]["opportunity_id"], "assessment-funnel-delivery-proof")

    def test_skips_complete_rows_unless_rescore_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "opportunities.json"
            log_path = Path(tmp) / "axis_scores.jsonl"
            engine.save_portfolio(
                {
                    "schema": "fpai_opportunity_portfolio_v1",
                    "opportunities": [
                        {
                            "id": "complete",
                            "title": "Complete",
                            "questions": {"problem": "Already scored."},
                            "axes": AXES,
                        }
                    ],
                },
                ledger,
            )
            calls = 0

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                nonlocal calls
                calls += 1
                return subprocess.CompletedProcess(command, 0, json.dumps({"axes": AXES}), "")

            result = scorer.score_missing_axes(ledger, log_path=log_path, runner=fake_runner)

            self.assertEqual(result["scored"], 0)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(calls, 0)
            self.assertFalse(log_path.exists())

    def test_next_domino_can_be_non_funnel_when_axes_outscore_it(self) -> None:
        funnel_axes = dict(AXES, pain=5, market=5, compounding=5, constraint=4, leverage=4, proof_speed=4)
        voice_axes = dict(AXES, pain=10, market=9, compounding=9, constraint=10, leverage=10, proof_speed=10)
        portfolio = {
            "schema": "fpai_opportunity_portfolio_v1",
            "opportunities": [
                {
                    "id": "assessment-funnel-delivery-proof",
                    "title": "Assessment Funnel Delivery Proof",
                    "axes": funnel_axes,
                    "topple": {"gate": "ai_reversible"},
                },
                {
                    "id": "ai-voice-receptionist",
                    "title": "AI Voice Receptionist",
                    "axes": voice_axes,
                    "topple": {"gate": "codex_build"},
                },
            ],
        }

        view = engine.ranked(portfolio)

        self.assertEqual(view["next_domino"][0]["id"], "ai-voice-receptionist")
        self.assertIsNotNone(view["next_domino"][0]["next_domino_score"])

    def test_liveness_clamps_live_traffic_ahead_of_unbuilt_rescore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "opportunities.json"
            log_path = Path(tmp) / "axis_scores.jsonl"
            engine.save_portfolio(
                {
                    "schema": "fpai_opportunity_portfolio_v1",
                    "opportunities": [
                        {
                            "id": "assessment-funnel-delivery-proof",
                            "title": "Assessment Funnel Delivery Proof",
                            "questions": {"problem": "Live assessment funnel with ad traffic."},
                            "axes": AXES,
                            "liveness": {"deployed": True, "traffic_clicks": 81, "lead_worker_active": True},
                            "topple": {"gate": "ai_reversible"},
                        },
                        {
                            "id": "resource-optimization-audit",
                            "title": "Resource Optimization Audit",
                            "questions": {"problem": "Unbuilt audit product."},
                            "axes": AXES,
                            "liveness": {"unbuilt": True},
                            "topple": {"gate": "james_reserved"},
                        },
                    ],
                },
                ledger,
            )

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                self.assertIn('"live_state"', command[2])
                if "assessment-funnel-delivery-proof" in command[2]:
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        json.dumps({"axes": dict(AXES, market=5, time_to_first_dollar=7, proof_speed=4)}),
                        "",
                    )
                return subprocess.CompletedProcess(command, 0, json.dumps({"axes": dict(AXES, time_to_first_dollar=1)}), "")

            result = scorer.score_missing_axes(
                ledger,
                log_path=log_path,
                runner=fake_runner,
                rescore_all=True,
                now="2026-07-05T16:00:00Z",
                liveness_paths=[],
            )

            portfolio = engine.load_portfolio(ledger)
            rows = {row["id"]: row for row in portfolio["opportunities"]}
            funnel = rows["assessment-funnel-delivery-proof"]
            unbuilt = rows["resource-optimization-audit"]
            self.assertEqual(funnel["axes"]["time_to_first_dollar"], 2.0)
            self.assertGreaterEqual(unbuilt["axes"]["time_to_first_dollar"], 3.0)
            self.assertEqual(funnel["axes"]["proof_speed"], 8.0)
            self.assertTrue(result["liveness_inputs"]["assessment-funnel-delivery-proof"]["live_with_traffic"])
            self.assertTrue(result["liveness_inputs"]["resource-optimization-audit"]["unbuilt"])

            view = engine.ranked(portfolio)
            ranked_ids = [row["id"] for row in view["next_domino"][:2]]
            self.assertLessEqual(ranked_ids.index("assessment-funnel-delivery-proof"), ranked_ids.index("resource-optimization-audit"))

            logs = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            funnel_log = next(row for row in logs if row["opportunity_id"] == "assessment-funnel-delivery-proof")
            self.assertTrue(funnel_log["liveness"]["live_with_traffic"])
            self.assertEqual(funnel_log["calibration"][0]["axis"], "time_to_first_dollar")


if __name__ == "__main__":
    unittest.main()
