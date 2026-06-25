from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from curator.tool_mastery import learn
from curator.tool_mastery.loader import get_mastery_context, inject_mastery


REQUIRED_SECTIONS = (
    "## What it does best",
    "## Optimal use patterns (concrete, with examples)",
    "## Anti-patterns (what silently degrades it)",
    "## Effort/parameter settings for this system",
    "## Key constraints and hard limits",
    "## How to detect it's not performing well",
    "## Last updated + source",
)


class ToolMasteryLoaderTests(unittest.TestCase):
    def test_get_mastery_context_returns_content_for_seeded_tools(self) -> None:
        for tool in ("claude_fable5", "codex", "claude_review", "stripe", "brevo", "hermes", "ollama"):
            with self.subTest(tool=tool):
                context = get_mastery_context(tool, max_tokens=80)
                self.assertTrue(context.startswith(f"[{tool} mastery]"))
                self.assertIn("Optimal use patterns", context)
                self.assertIn("Anti-patterns", context)

    def test_inject_mastery_prepends_context(self) -> None:
        prompt = "Review this diff."
        injected = inject_mastery(prompt, "claude_review")
        self.assertTrue(injected.startswith("[claude_review mastery]"))
        self.assertTrue(injected.endswith(prompt))

    def test_inject_mastery_disable_switch_returns_prompt_unchanged(self) -> None:
        with mock.patch.dict(os.environ, {"TOOL_MASTERY_DISABLE": "1"}):
            self.assertEqual(inject_mastery("plain prompt", "claude_review"), "plain prompt")

    def test_unknown_tool_returns_empty_string(self) -> None:
        self.assertEqual(get_mastery_context("missing_tool"), "")
        self.assertEqual(get_mastery_context("../stripe"), "")

    def test_learn_tool_skips_human_edited_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cards = root / "docs" / "tool_mastery"
            cards.mkdir(parents=True)
            card = cards / "human.md"
            card.write_text("# human Mastery Card\n\n## What it does best\nHuman edited.\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"TOOL_MASTERY_REPO_ROOT": tmp}):
                with mock.patch.object(learn, "_run_claude", side_effect=AssertionError("should not run")):
                    self.assertEqual(learn.learn_tool("human", "source text"), str(card))
                    self.assertEqual(card.read_text(encoding="utf-8"), "# human Mastery Card\n\n## What it does best\nHuman edited.\n")

    def test_refresh_all_skips_human_and_relearns_auto_generated(self) -> None:
        generated = "\n".join(
            [
                "## What it does best",
                "Does the job.",
                "## Optimal use patterns (concrete, with examples)",
                "Use focused examples.",
                "## Anti-patterns (what silently degrades it)",
                "Avoid vague prompts.",
                "## Key constraints and hard limits",
                "No unsafe effects.",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cards = root / "docs" / "tool_mastery"
            cards.mkdir(parents=True)
            auto = cards / "auto_tool.md"
            human = cards / "human_tool.md"
            auto.write_text("[AUTO-GENERATED]\n# auto_tool Mastery Card\n\nold", encoding="utf-8")
            human.write_text("# human_tool Mastery Card\n\nold", encoding="utf-8")
            with mock.patch.dict(os.environ, {"TOOL_MASTERY_REPO_ROOT": tmp}):
                with mock.patch.object(learn, "_run_claude", return_value=generated):
                    refreshed = learn.refresh_all()
            self.assertEqual(refreshed, [str(auto)])
            self.assertIn("Use focused examples.", auto.read_text(encoding="utf-8"))
            self.assertEqual(human.read_text(encoding="utf-8"), "# human_tool Mastery Card\n\nold")

    def test_refresh_all_uses_recorded_source_when_available(self) -> None:
        generated = "\n".join(
            [
                "## What it does best",
                "Does the job.",
                "## Optimal use patterns (concrete, with examples)",
                "Use source docs.",
                "## Anti-patterns (what silently degrades it)",
                "Avoid stale summaries.",
                "## Key constraints and hard limits",
                "No unsafe effects.",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            cards = Path(tmp) / "docs" / "tool_mastery"
            cards.mkdir(parents=True)
            auto = cards / "auto_tool.md"
            auto.write_text(
                "[AUTO-GENERATED]\n# auto_tool Mastery Card\n\n"
                "## Last updated + source\nGenerated from: https://example.test/source\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"TOOL_MASTERY_REPO_ROOT": tmp}):
                with mock.patch.object(learn, "_read_source", return_value="fresh source") as read_source:
                    with mock.patch.object(learn, "_run_claude", return_value=generated):
                        learn.refresh_all()
            read_source.assert_called_once_with("https://example.test/source")

    def test_seeded_cards_contain_all_required_sections(self) -> None:
        root = Path(__file__).resolve().parents[2]
        for path in sorted((root / "docs" / "tool_mastery").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(card=path.name):
                for section in REQUIRED_SECTIONS:
                    self.assertIn(section, text)


if __name__ == "__main__":
    unittest.main()
