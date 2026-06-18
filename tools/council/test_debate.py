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


if __name__ == "__main__":
    unittest.main()
