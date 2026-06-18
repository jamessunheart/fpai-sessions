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
        )

        portrait = synthesize.render_portrait(evidence, generated_at="2026-06-18T19:30:00Z")

        self.assertIn("generated_by: d102 self-portrait synthesis agent", portrait)
        self.assertIn("## The gap", portrait)
        self.assertIn("brain_index.corrections", portrait)
        self.assertIn("awareness=64/100", portrait)

    def test_self_portrait_context_is_bounded_to_evidence_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SELF_PORTRAIT.md"
            path.write_text(
                "# Self-Portrait\n\n"
                "## Who I think I am\n\n- stated\n\n"
                "## What the evidence shows\n\n- measured\n\n"
                "## The gap\n\n- delta\n\n"
                "## What I'm becoming\n\n- trajectory\n\n"
                "## Blind spots (unobservable)\n\n- missing DB\n",
                encoding="utf-8",
            )

            context = synthesize.self_portrait_context(path, max_chars=500)

        self.assertIn("SELF-PORTRAIT CONTEXT - COUNCIL-OPEN", context)
        self.assertIn("## The gap", context)
        self.assertNotIn("## Who I think I am", context)

    def test_collect_evidence_redacts_personal_markers_from_model_dna(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "MODEL_DNA.md"
            ops = root / "ops.jsonl"
            consciousness = root / "consciousness"
            scout = root / "scout.jsonl"
            consciousness.mkdir()
            model.write_text("- James-facing routing keeps Telegram concise.\n", encoding="utf-8")
            ops.write_text('{"event":"succeeded","loop":"council","detail":"ok"}\n', encoding="utf-8")
            scout.write_text('{"proposal":"reuse tool"}\n', encoding="utf-8")

            evidence = synthesize.collect_evidence(
                model_dna=model,
                ops_ledger=ops,
                consciousness_dir=consciousness,
                scout_log=scout,
            )

        self.assertEqual(evidence.ops_counts["succeeded"], 1)
        self.assertIn("[personal]-facing routing keeps [personal] concise.", evidence.model_dna_signals[0])


if __name__ == "__main__":
    unittest.main()
