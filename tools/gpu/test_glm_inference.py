import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tools.gpu import budget_guard, glm_inference


class GLMInferenceTest(unittest.TestCase):
    def test_falls_back_to_claude_when_endpoint_unavailable(self):
        def runner(*_args, **_kwargs):
            return subprocess.CompletedProcess([], 0, "fallback answer\n", "")

        with mock.patch.dict(os.environ, {}, clear=True):
            text = glm_inference.call_glm(
                [{"role": "user", "content": "hello"}],
                fallback_runner=runner,
            )

        self.assertEqual(text, "fallback answer")

    def test_success_posts_openai_messages_and_logs_gpu_seconds(self):
        root = Path(tempfile.mkdtemp(prefix="fpai-glm-test-"))
        ledger = root / "ops.jsonl"
        seen = {}

        def poster(url, payload, api_key, timeout):
            seen["url"] = url
            seen["payload"] = payload
            seen["api_key"] = api_key
            seen["timeout"] = timeout
            return {
                "output": {
                    "choices": [{"message": {"content": "sovereign answer"}}],
                    "gpu_seconds": 3.25,
                }
            }

        decision = budget_guard.BudgetDecision(True, 1.0, 50.0, 45.0, "within budget")
        text = glm_inference.call_glm(
            [{"role": "user", "content": "hello"}],
            endpoint_id="endpoint-123",
            api_key="rp_test",
            ops_ledger=ledger,
            poster=poster,
            budget_checker=lambda: decision,
        )

        self.assertEqual(text, "sovereign answer")
        self.assertTrue(seen["url"].endswith("/endpoint-123/runsync"))
        self.assertEqual(seen["payload"]["input"]["messages"][0]["content"], "hello")
        row = json.loads(ledger.read_text(encoding="utf-8").strip())
        self.assertEqual(row["loop"], "glm_runpod")
        self.assertEqual(row["event"], "succeeded")
        self.assertEqual(row["gpu_seconds"], 3.25)


if __name__ == "__main__":
    unittest.main()

