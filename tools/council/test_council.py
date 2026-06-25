import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.council import debate, glm_client


class CouncilGLMRoutingTest(unittest.TestCase):
    def _clean_glm_env(self) -> dict[str, str]:
        env = dict(os.environ)
        for key in ("GLM_API_KEY", "GLM_LOCAL_URL", "GLM_COUNCIL_DISABLE"):
            env.pop(key, None)
        return env

    def test_without_glm_key_all_lenses_fall_back_to_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, self._clean_glm_env(), clear=True):
            calls = []

            def fake_claude(system_prompt: str, user_prompt: str, *, effort: str = "xhigh") -> str:
                calls.append(system_prompt)
                return "claude answer"

            with mock.patch.object(debate, "run_claude", side_effect=fake_claude):
                lenses, model_log = debate.run_lenses("context", ops_ledger=Path(tmp) / "ops.jsonl")

        self.assertEqual(set(lenses), {"pragmatist", "visionary", "skeptic"})
        self.assertEqual(len(calls), 3)
        self.assertEqual([row["model"] for row in model_log], ["claude -p", "claude -p", "claude -p"])
        self.assertEqual(model_log[0]["fallback_reason"], "not_configured")

    def test_with_glm_key_pragmatist_uses_glm_others_use_claude(self) -> None:
        env = self._clean_glm_env()
        env["GLM_API_KEY"] = "test-key"
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(glm_client, "call_glm", return_value="glm pragmatic proof"), mock.patch.object(
                glm_client,
                "get_last_usage",
                return_value={"model": "glm-5.2", "tokens_in": 1000, "tokens_out": 500, "cost_usd": 0.0036},
            ), mock.patch.object(debate, "run_claude", return_value="claude lens"):
                lenses, model_log = debate.run_lenses("context", ops_ledger=Path(tmp) / "ops.jsonl")

        self.assertEqual(lenses["pragmatist"], "glm pragmatic proof")
        self.assertEqual(model_log[0]["model"], "glm-5.2")
        self.assertEqual(model_log[0]["provider"], "glm")
        self.assertEqual([row["model"] for row in model_log[1:]], ["claude -p", "claude -p"])

    def test_glm_cost_tracked_in_ops_ledger(self) -> None:
        env = self._clean_glm_env()
        env["GLM_API_KEY"] = "test-key"
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, env, clear=True):
            ledger = Path(tmp) / "ops.jsonl"
            with mock.patch.object(glm_client, "call_glm", return_value="ship the proof"), mock.patch.object(
                glm_client,
                "get_last_usage",
                return_value={"model": "glm-5.2", "tokens_in": 1000, "tokens_out": 500},
            ):
                text, meta = debate.run_pragmatist("system", "user", ops_ledger=ledger)

            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(text, "ship the proof")
        self.assertEqual(meta["model"], "glm-5.2")
        self.assertEqual(rows[0]["label"], "council.pragmatist")
        self.assertEqual(rows[0]["model"], "glm-5.2")
        self.assertEqual(rows[0]["tokens_in"], 1000)
        self.assertEqual(rows[0]["tokens_out"], 500)
        self.assertEqual(rows[0]["cost_usd"], 0.0036)

    def test_glm_falls_back_before_daily_cap_would_be_exceeded(self) -> None:
        env = self._clean_glm_env()
        env["GLM_API_KEY"] = "test-key"
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, env, clear=True):
            ledger = Path(tmp) / "ops.jsonl"
            debate.append_glm_ops_ledger(
                {"tokens_in": 1, "tokens_out": 1, "cost_usd": 4.999},
                ops_ledger=ledger,
                model="glm-5.2",
            )
            with mock.patch.object(glm_client, "call_glm") as call_glm, mock.patch.object(
                debate, "run_claude", return_value="claude fallback"
            ):
                text, meta = debate.run_pragmatist("system", "user", ops_ledger=ledger)

        self.assertEqual(text, "claude fallback")
        self.assertEqual(meta["model"], "claude -p")
        self.assertEqual(meta["fallback_reason"], "daily_cap")
        call_glm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
