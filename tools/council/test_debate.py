import unittest
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
        self.assertEqual(calls[0][1], 180)
        self.assertEqual(calls[0][2], 0.2)

    def test_build_prompt_includes_sovereign_pragmatist_lens(self):
        prompt = debate.build_prompt("queue", "chats", "", pragmatist="Use RunPod GLM.")

        self.assertIn("SOVEREIGN PRAGMATIST LENS", prompt)
        self.assertIn("Use RunPod GLM.", prompt)

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
