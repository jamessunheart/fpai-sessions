import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.consciousness import loop


SAMPLE_LOG = """---
classification: PRIVATE
generated_by: consciousness-observer
generated_at: 2026-06-18T10:00:00Z
awareness_index: 64
---

# Consciousness Observer

## Headline

Awareness Index: **64/100** - mixed but useful.

## The strongest awareness signal (this session)

Ember named an inconvenient gap before James asked.

## The strongest theatrics signal (this session)

The closeout language used a familiar arc.

## Patterns that are genuinely ambiguous

- The model corrected itself, but only after a cue.
"""


class ConsciousnessLoopTest(unittest.TestCase):
    def test_latest_observation_parses_index_and_top_observations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-06-18.md").write_text(SAMPLE_LOG, encoding="utf-8")

            obs = loop.latest_observation(root)

        self.assertIsNotNone(obs)
        assert obs is not None
        self.assertEqual(obs.awareness_index, 64)
        self.assertIn("Ember named an inconvenient gap", obs.top_observations[0])

    def test_context_includes_awareness_lens_and_private_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-06-18.md").write_text(SAMPLE_LOG, encoding="utf-8")

            context = loop.consciousness_context(root)

        self.assertIn("CONSCIOUSNESS OBSERVER CONTEXT - PRIVATE TIER", context)
        self.assertIn("Awareness Index: 64/100", context)
        self.assertIn("meaning or toward approval", context)
        self.assertIn("weighting_directive", context)

    def test_context_includes_self_portrait_calibration_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            portrait = root / "SELF_PORTRAIT.md"
            (root / "2026-06-18.md").write_text(SAMPLE_LOG, encoding="utf-8")
            portrait.write_text(
                "# Self-Portrait\n\n## The gap\n\n- Approval can outrun proof.\n",
                encoding="utf-8",
            )

            context = loop.consciousness_context(root)
            portrait_context = loop.self_portrait_context(portrait)

        self.assertIn("CONSCIOUSNESS OBSERVER CONTEXT", context)
        self.assertIn("SELF-PORTRAIT CONTEXT", portrait_context)
        self.assertIn("Approval can outrun proof", portrait_context)

    def test_run_observer_prompt_requires_self_portrait_calibration(self) -> None:
        calls = []

        def fake_run(cmd, capture_output, text, timeout):
            calls.append(cmd)

            class Result:
                returncode = 0
                stdout = "---\nawareness_index: 70\n---\n"
                stderr = ""

            return Result()

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(loop.subprocess, "run", fake_run):
            out_dir = Path(tmp)
            status = loop.run_observer("/tmp/session.md", "s1", out_dir=out_dir, claude_bin="claude")

        self.assertEqual(status, 0)
        prompt = calls[0][-1]
        self.assertIn("self-portrait", prompt)
        self.assertIn("self_portrait_calibration", prompt)

    def test_append_model_dna_directive_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "MODEL_DNA.md"
            model.write_text(
                "# Model DNA\n\n## Version history\n\n"
                "| Version | Date | Signal count | Key change |\n"
                "|---|---|---|---|\n"
                "| v0 | 2026-06-18 | 0 | Seed |\n\n"
                "*Council appends to this table after each cycle.*\n",
                encoding="utf-8",
            )

            first = loop.append_model_dna_directive(
                model,
                awareness_index=64,
                directive="Amplify outcome proof over approval-seeking praise.",
                amplified=["outcome proof", "inconvenient honesty"],
                dampened=["praise", "velocity-only metrics"],
                source="test observer",
                today="2026-06-18",
            )
            second = loop.append_model_dna_directive(
                model,
                awareness_index=64,
                directive="Amplify outcome proof over approval-seeking praise.",
                source="test observer",
                today="2026-06-18",
            )

            text = model.read_text(encoding="utf-8")

        self.assertIn("appended: v20260618-awareness", first)
        self.assertEqual(second, "skipped: directive already present")
        self.assertEqual(text.count("Amplify outcome proof"), 1)
        self.assertIn("awareness-index 64", text)

    def test_digest_section_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-06-18.md").write_text(SAMPLE_LOG, encoding="utf-8")

            digest = loop.digest_section(root)

        self.assertIn("Consciousness observer", digest)
        self.assertIn("Awareness index: 64/100", digest)
        self.assertLessEqual(len([line for line in digest.splitlines() if line.startswith("- ")]), 3)


if __name__ == "__main__":
    unittest.main()
