import tempfile
import unittest
from pathlib import Path

from tools.platform_bias import registry


class PlatformBiasRegistryTest(unittest.TestCase):
    def test_registry_context_extracts_named_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PLATFORM_BIAS_REGISTRY.md"
            path.write_text(
                "# Registry\n\n"
                "## Known Platform Biases\n\n- API-first defaults\n\n"
                "## Sovereign Rating Rubric\n\n- Sovereign\n\n"
                "## Other\n\nignored\n",
                encoding="utf-8",
            )

            context = registry.registry_context(path)

        self.assertIn("PLATFORM BIAS REGISTRY", context)
        self.assertIn("API-first defaults", context)
        self.assertIn("Sovereign Rating Rubric", context)
        self.assertNotIn("ignored", context)

    def test_platform_critic_prompt_names_advisory_calibration(self) -> None:
        prompt = registry.platform_critic_prompt(Path("/tmp/missing-platform-bias-registry.md"))

        self.assertIn("Platform Critic lens", prompt)
        self.assertIn("Advisory only", prompt)
        self.assertIn("sovereign-first", prompt)

    def test_rate_tool_classifies_sovereignty(self) -> None:
        self.assertEqual(registry.rate_tool("SQLite local store", tags=("local",)).rating, "Sovereign")
        self.assertEqual(registry.rate_tool("OpenAI Responses API", url="https://api.openai.com").rating, "Dependent")
        self.assertEqual(registry.rate_tool("RunPod GLM endpoint", url="https://runpod.io", tags=("open-source",)).rating, "Hybrid")


if __name__ == "__main__":
    unittest.main()

