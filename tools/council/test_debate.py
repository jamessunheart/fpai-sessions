import unittest
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from tools.council import debate


class CouncilDebateTest(unittest.TestCase):
    def test_pragmatist_uses_glm_caller(self):
        calls = []

        def glm(messages, max_tokens, temperature):
            calls.append((messages, max_tokens, temperature))
            return "Build the smallest budget-guarded GLM adapter first."

        lens = debate.pragmatist_voice("queue\nchat", glm_caller=glm)

        self.assertIn("GLM adapter", lens)
        self.assertEqual(calls[0][0][0]["role"], "system")
        self.assertIn("Pragmatist lens", calls[0][0][0]["content"])
        self.assertEqual(calls[0][1], 180)
        self.assertEqual(calls[0][2], 0.2)

    def test_council_pragmatist_prompt_uses_prompt_efficiency_renderer(self):
        with mock.patch(
            "tools.prompt_efficiency.gepa_loop.render_council_pragmatist_prompt",
            return_value="FPAI council Pragmatist lens: optimized pending prompt.",
        ):
            prompt = debate._council_pragmatist_prompt()

        self.assertEqual(prompt, "FPAI council Pragmatist lens: optimized pending prompt.")

    def test_build_prompt_includes_sovereign_pragmatist_lens(self):
        prompt = debate.build_prompt("queue", "chats", "", pragmatist="Use RunPod GLM.")

        self.assertIn("SOVEREIGN PRAGMATIST LENS", prompt)
        self.assertIn("Use RunPod GLM.", prompt)

    def test_build_prompt_includes_opportunity_portfolio(self):
        with mock.patch(
            "tools.allocation.opportunity_engine.council_context",
            return_value="OPPORTUNITY PORTFOLIO\n- Resource Optimization Audit: allocation=26.5",
        ):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("OPPORTUNITY PORTFOLIO", prompt)
        self.assertIn("Resource Optimization Audit", prompt)

    def test_run_claude_json_parses_wrapped_json(self):
        def runner(args, **kwargs):
            self.assertEqual(args[0], "/usr/bin/claude")
            return subprocess.CompletedProcess(
                args,
                0,
                'thinking...\n{"propose": false, "title": "No build"}\n',
                "",
            )

        with mock.patch.object(debate.shutil, "which", return_value="/usr/bin/claude"):
            payload, result = debate.run_claude_json("prompt", runner=runner)

        self.assertFalse(payload["propose"])
        self.assertEqual(result.returncode, 0)

    def test_run_claude_json_reports_cli_failure(self):
        def runner(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, "", "auth failed")

        with mock.patch.object(debate.shutil, "which", return_value="/usr/bin/claude"):
            with self.assertRaisesRegex(RuntimeError, "auth failed"):
                debate.run_claude_json("prompt", runner=runner)

    def test_gpt_voice_logs_and_skips_cli_failure(self):
        ops = []

        def runner(args, **kwargs):
            self.assertEqual(args[0], "/usr/bin/codex")
            return subprocess.CompletedProcess(args, 2, "", "codex auth missing")

        with mock.patch.object(debate.shutil, "which", return_value="/usr/bin/codex"):
            with mock.patch.object(debate, "_ops", lambda event, detail, nxt="": ops.append((event, detail))):
                voice = debate.gpt_voice("queue", runner=runner)

        self.assertEqual(voice, "")
        self.assertEqual(ops[0][0], "gpt_voice_error")
        self.assertIn("codex auth missing", ops[0][1])

    def test_pragmatist_voice_logs_and_skips_glm_failure(self):
        ops = []

        def failing_glm(*_args, **_kwargs):
            raise RuntimeError("glm unavailable")

        with mock.patch.object(debate, "_ops", lambda event, detail, nxt="": ops.append((event, detail))):
            voice = debate.pragmatist_voice("queue", glm_caller=failing_glm)

        self.assertEqual(voice, "")
        self.assertEqual(ops[0][0], "pragmatist_voice_error")
        self.assertIn("glm unavailable", ops[0][1])

    def test_build_prompt_includes_platform_critic_lens(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("platform_critic", prompt)
        self.assertIn("Platform Critic lens", prompt)
        self.assertIn("PLATFORM BIAS REGISTRY", prompt)

    def test_platform_critic_has_kill_switch(self):
        with mock.patch.dict("os.environ", {"PLATFORM_CRITIC_DISABLE": "1"}):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertNotIn("platform_critic", prompt)
        self.assertNotIn("Platform Bias Registry", prompt)

    def test_resources_text_loads_available_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            state = repo / "core" / "STATE"
            state.mkdir(parents=True)
            (state / "AVAILABLE_RESOURCES.md").write_text(
                "# Available Resources\n\n## CLIs\n\n- git: /usr/bin/git\n",
                encoding="utf-8",
            )
            with mock.patch.object(debate, "REPO", str(repo)):
                resources = debate._resources_text()

        self.assertIn("AVAILABLE RESOURCES", resources)
        self.assertIn("- git: /usr/bin/git", resources)

    def test_build_prompt_can_reference_inventory_tool(self):
        prompt = debate.build_prompt(
            "queue",
            "chats",
            "\n\nAVAILABLE RESOURCES — prefer proposals that use already-installed tools when relevant:\n"
            "# Available Resources\n\n## CLIs\n\n- git: /usr/bin/git\n",
        )

        self.assertIn("AVAILABLE RESOURCES", prompt)
        self.assertIn("- git: /usr/bin/git", prompt)

    def test_build_prompt_includes_awareness_context_when_available(self):
        class FakeConsciousnessLoop:
            @staticmethod
            def consciousness_context():
                return "CONSCIOUSNESS OBSERVER CONTEXT - PRIVATE TIER\nAwareness Index: 64/100"

        with mock.patch.object(debate, "consciousness_loop", FakeConsciousnessLoop):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("Private consciousness-observer context", prompt)
        self.assertIn("Awareness Index: 64/100", prompt)

    def test_build_prompt_includes_self_portrait_context_when_available(self):
        class FakeSelfPortrait:
            @staticmethod
            def self_portrait_context(path):
                return "SELF-PORTRAIT CONTEXT - COUNCIL-OPEN\n## The gap\n- Approval can outrun proof."

        with mock.patch.object(debate, "self_portrait_synth", FakeSelfPortrait):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("Self-portrait context for Awareness lens", prompt)
        self.assertIn("Approval can outrun proof", prompt)
        self.assertIn("who the system actually is", prompt)

    def test_council_result_can_update_model_dna(self):
        class FakeObservation:
            awareness_index = 64
            path = Path("2026-06-18.md")

        class FakeConsciousnessLoop:
            calls = []

            @staticmethod
            def latest_observation(_dir=None):
                return FakeObservation()

            @classmethod
            def maybe_append_from_council(cls, result):
                cls.calls.append(result)
                return "appended: v20260618-awareness"

        result = {
            "weighting_directive": "Amplify outcome proof over approval-seeking praise.",
            "signal_types_amplified": ["outcome proof"],
            "signal_types_dampened": ["praise"],
        }

        with mock.patch.object(debate, "consciousness_loop", FakeConsciousnessLoop):
            status = debate.consciousness_loop.maybe_append_from_council(result)

        self.assertEqual(status, "appended: v20260618-awareness")
        self.assertEqual(FakeConsciousnessLoop.calls[0]["weighting_directive"], result["weighting_directive"])


if __name__ == "__main__":
    unittest.main()
