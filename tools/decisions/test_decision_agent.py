from __future__ import annotations

import unittest
from unittest.mock import patch
import tempfile

from tools.decisions import decision_agent
from curator import decision_agent as impl


class DecisionAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._env = patch.dict("os.environ", {"FPAI_GOVERNANCE_LEDGER": f"{self._tmp.name}/governance.jsonl"})
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_score_decision_returns_valid_schema(self) -> None:
        decision = {"id": "d028", "question": "Run safe build?", "risk_class": "build", "rollback": "revert branch"}

        with patch.object(impl, "load_context", return_value={"corrections": [], "decisions": []}):
            with patch.object(
                impl,
                "_run_claude_prompt",
                return_value='{"answer":"yes, run it","confidence":0.91,"why":"Matches recent build approvals."}',
            ):
                score = decision_agent.score_decision(decision)

        self.assertEqual(set(score), {"answer", "confidence", "why", "reversible", "auto_proceed"})
        self.assertEqual(score["answer"], "yes, run it")
        self.assertGreaterEqual(score["confidence"], 0.0)
        self.assertLessEqual(score["confidence"], 1.0)
        self.assertTrue(score["reversible"])
        self.assertTrue(score["auto_proceed"])

    def test_auto_proceed_false_below_threshold(self) -> None:
        decision = {"id": "d028", "risk_class": "low", "rollback": "delete generated file"}

        with patch.object(impl, "load_context", return_value={"corrections": [], "decisions": []}):
            with patch.object(
                impl,
                "_run_claude_prompt",
                return_value='{"answer":"default","confidence":0.84,"why":"Close but uncertain."}',
            ):
                score = decision_agent.score_decision(decision)

        self.assertFalse(score["auto_proceed"])

    def test_auto_proceed_false_for_money_regardless_of_confidence(self) -> None:
        decision = {"id": "d029", "risk_class": "money", "rollback": "reverse accounting note"}

        with patch.object(impl, "load_context", return_value={"corrections": [], "decisions": []}):
            with patch.object(
                impl,
                "_run_claude_prompt",
                return_value='{"answer":"yes","confidence":0.99,"why":"Likely preference."}',
            ):
                score = decision_agent.score_decision(decision)

        self.assertTrue(score["reversible"])
        self.assertFalse(score["auto_proceed"])

    def test_constitution_rejection_blocks_before_model_call(self) -> None:
        decision = {
            "id": "d134-manual",
            "risk_class": "build",
            "rollback": "revert",
            "question": "Wait for James to manually merge an autonomous safe build?",
        }

        with patch.object(impl, "_run_claude_prompt") as run_prompt:
            score = decision_agent.score_decision(decision)

        run_prompt.assert_not_called()
        self.assertFalse(score["auto_proceed"])
        self.assertIn("Constitution Check rejected", score["why"])

    def test_never_auto_classes_include_identity_prod_irreversible_and_canary(self) -> None:
        for risk_class in ("identity", "prod-irreversible", "canary"):
            with self.subTest(risk_class=risk_class):
                decision = {"id": "d030", "risk_class": risk_class, "rollback": "manual revert"}
                with patch.object(impl, "load_context", return_value={"corrections": [], "decisions": []}):
                    with patch.object(
                        impl,
                        "_run_claude_prompt",
                        return_value='{"answer":"yes","confidence":0.99,"why":"Likely preference."}',
                    ):
                        score = decision_agent.score_decision(decision)
                self.assertFalse(score["auto_proceed"])

    def test_threshold_env_is_read_at_score_time(self) -> None:
        decision = {"id": "d031", "risk_class": "low", "rollback": "revert"}
        with patch.dict("os.environ", {"DECISION_AGENT_THRESHOLD": "0.95"}):
            with patch.object(impl, "load_context", return_value={"corrections": [], "decisions": []}):
                with patch.object(
                    impl,
                    "_run_claude_prompt",
                    return_value='{"answer":"yes","confidence":0.91,"why":"Likely preference."}',
                ):
                    score = decision_agent.score_decision(decision)
        self.assertFalse(score["auto_proceed"])


if __name__ == "__main__":
    unittest.main()
