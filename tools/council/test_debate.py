import unittest

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


if __name__ == "__main__":
    unittest.main()
