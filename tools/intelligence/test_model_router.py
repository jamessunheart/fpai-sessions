#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.intelligence import model_router, provider_health


class ModelRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = mock.patch.dict(os.environ, {"MODEL_ROUTER_SKIP_OLLAMA_PULL": "1"}, clear=False)
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()

    def test_t1_used_when_t0_fails(self) -> None:
        def fake_call(provider: str, prompt: str) -> tuple[str, float]:
            if provider == "claude":
                raise model_router.ProviderFailure(provider, 0, "not logged in")
            if provider == "ollama":
                return "local answer", 0.0
            raise AssertionError(provider)

        with mock.patch.object(model_router, "load_routing", return_value={"review": ["claude", "ollama"]}), \
             mock.patch.object(model_router, "_call_provider", side_effect=fake_call), \
             mock.patch.object(model_router, "_append_ops") as ops:
            result = model_router.call_model("prompt", "review")
        self.assertEqual(result["provider"], "ollama")
        self.assertEqual(result["tier"], 1)
        self.assertEqual(result["cost_estimate"], 0.0)
        events = [call.args[1] for call in ops.call_args_list]
        self.assertIn("model_degraded", events)

    def test_t2_used_when_t0_and_t1_fail(self) -> None:
        def fake_call(provider: str, prompt: str) -> tuple[str, float]:
            if provider in {"claude", "ollama"}:
                raise model_router.ProviderFailure(provider, model_router.provider_tier(provider), "down")
            if provider == "openai-api":
                return "metered answer", 0.012
            raise AssertionError(provider)

        with mock.patch.object(model_router, "load_routing", return_value={"review": ["claude", "ollama", "openai-api"]}), \
             mock.patch.object(model_router, "_call_provider", side_effect=fake_call):
            result = model_router.call_model("prompt", "review")
        self.assertEqual(result["provider"], "openai-api")
        self.assertEqual(result["tier"], 2)
        self.assertGreater(result["cost_estimate"], 0)

    def test_degraded_mode_triggered_when_all_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flag = Path(tmp) / ".model_outage"
            alert = Path(tmp) / ".model_outage_alerted"
            with mock.patch.object(model_router, "OUTAGE_FLAG", flag), \
                 mock.patch.object(model_router, "OUTAGE_ALERT", alert), \
                 mock.patch.object(model_router, "load_routing", return_value={"review": ["claude", "ollama"]}), \
                 mock.patch.object(model_router, "_send_tg") as send, \
                 mock.patch.object(
                     model_router,
                     "_call_provider",
                     side_effect=lambda provider, prompt: (_ for _ in ()).throw(
                         model_router.ProviderFailure(provider, model_router.provider_tier(provider), "down")
                     ),
                 ):
                with self.assertRaises(RuntimeError):
                    model_router.call_model("prompt", "review")
            self.assertTrue(flag.exists())
            send.assert_called_once()

    def test_t0_t1_cost_is_zero_and_t2_cost_is_nonzero(self) -> None:
        with mock.patch.object(model_router, "load_routing", return_value={"review": ["claude"]}), \
             mock.patch.object(model_router, "_call_provider", return_value=("ok", 0.0)):
            zero = model_router.call_model("prompt", "review")
        self.assertEqual(zero["cost_estimate"], 0.0)

        with mock.patch.object(model_router, "load_routing", return_value={"review": ["openai-api"]}), \
             mock.patch.object(model_router, "_call_provider", return_value=("ok", 0.01)):
            paid = model_router.call_model("prompt", "review")
        self.assertGreater(paid["cost_estimate"], 0.0)

    def test_routing_yaml_mapping_respected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "routing.yaml"
            path.write_text("review:\n  - ollama\n  - openai-api\n", encoding="utf-8")
            routing = model_router.load_routing(path)
        self.assertEqual(routing["review"], ["ollama", "openai-api"])

        with mock.patch.object(model_router, "load_routing", return_value=routing):
            self.assertEqual(model_router.route_for("review"), ["ollama", "openai-api"])
            self.assertEqual(model_router.route_for("review", tier_floor=2), ["openai-api"])

    def test_provider_health_returns_mocked_bools(self) -> None:
        outputs = iter([
            mock.Mock(returncode=0, stdout="ok"),
            mock.Mock(returncode=1, stdout="not logged in"),
            mock.Mock(returncode=0, stdout=json.dumps({"models": []})),
        ])
        with mock.patch.object(provider_health.subprocess, "run", side_effect=lambda *a, **k: next(outputs)), \
             mock.patch.object(provider_health, "_append_ops"):
            result = provider_health.check_provider_health()
        self.assertTrue(result["claude"])
        self.assertFalse(result["codex"])
        self.assertTrue(result["ollama"])
        self.assertIn("last_checked", result)


if __name__ == "__main__":
    unittest.main()
