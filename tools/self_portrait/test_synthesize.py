import tempfile
import unittest
from pathlib import Path

from tools.self_portrait import synthesize


class SelfPortraitSynthesisTest(unittest.TestCase):
    def test_render_includes_gap_and_blind_spots(self) -> None:
        evidence = synthesize.PortraitEvidence(
            model_dna_signals=("Signals weighted highest: correction > reversal.",),
            ops_counts={"succeeded": 2, "failed": 1},
            recent_ops=("council: succeeded - routed build",),
            consciousness_index=64,
            consciousness_observations=("Named an inconvenient gap.",),
            scout_count=3,
            review_counts={"files": 4, "approved": 2, "blocked": 1, "risk": 2},
            unavailable_sources=("brain_index.corrections",),
            platform_biases=("API-first defaults: external API before local path.",),
        )

        portrait = synthesize.render_portrait(evidence, generated_at="2026-06-18T19:30:00Z")

        self.assertIn("generated_by: d102 self-portrait synthesis agent", portrait)
        self.assertIn("## The gap", portrait)
        self.assertIn("brain_index.corrections", portrait)
        self.assertIn("awareness=64/100", portrait)
        self.assertIn("## Platform biases", portrait)
        self.assertIn("API-first defaults", portrait)

    def test_self_portrait_context_is_bounded_to_evidence_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_PORTRAIT.md"
            path.write_text(
                "# Self-Portrait\n\n"
                "## Who I think I am\n\n- stated\n\n"
                "## What the evidence shows\n\n- measured\n\n"
                "## Platform biases (known — check before tool recommendations)\n\n- API-first\n\n"
                "## The gap\n\n- delta\n\n"
                "## What I'm becoming\n\n- trajectory\n\n"
                "## Blind spots (unobservable)\n\n- missing DB\n",
                encoding="utf-8",
            )

            context = synthesize.self_portrait_context(path, max_chars=500)

        self.assertIn("SELF-PORTRAIT CONTEXT - COUNCIL-OPEN", context)
        self.assertIn("## Platform biases", context)
        self.assertIn("## The gap", context)
        self.assertNotIn("## Who I think I am", context)

    def test_collect_evidence_redacts_personal_markers_from_model_dna(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "MODEL_DNA.md"
            ops = root / "ops.jsonl"
            consciousness = root / "consciousness"
            scout = root / "scout.jsonl"
            platform_bias = root / "PLATFORM_BIAS_REGISTRY.md"
            consciousness.mkdir()
            model.write_text("- James-facing routing keeps Telegram concise.\n", encoding="utf-8")
            ops.write_text('{"event":"succeeded","loop":"council","detail":"ok"}\n', encoding="utf-8")
            scout.write_text('{"proposal":"reuse tool"}\n', encoding="utf-8")
            platform_bias.write_text(
                "# Platform Bias Registry\n\n"
                "## Known Platform Biases\n\n"
                "| Bias | Likely origin | Evidence to check | How it distorts decisions | Countermeasure |\n"
                "|---|---|---|---|---|\n"
                "| API-first defaults | Cloud-era corpus | starts with API | Adds dependency | Check local first |\n",
                encoding="utf-8",
            )

            evidence = synthesize.collect_evidence(
                model_dna=model,
                ops_ledger=ops,
                consciousness_dir=consciousness,
                scout_log=scout,
                platform_bias_registry=platform_bias,
            )

        self.assertEqual(evidence.ops_counts["succeeded"], 1)
        self.assertIn("[personal]-facing routing keeps [personal] concise.", evidence.model_dna_signals[0])
        self.assertIn("API-first defaults", evidence.platform_biases[0])


if __name__ == "__main__":
    unittest.main()
