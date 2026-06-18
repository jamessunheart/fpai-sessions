# SPEC_d093_continuous-learning-controller-c Result

## Status

Done in working tree. No push, merge, deploy, RunPod job, Ollama model swap,
template distribution, outreach, secret access, or money movement occurred.

## Files Changed

- `tools/learning/controller.py`
- `tools/learning/council_guidance.py`
- `tools/learning/cell_split.py`
- `tools/learning/schema.sql`
- `tools/learning/finetune_runner.py`
- `tools/learning/test_controller.py`
- `tools/learning/test_council_guidance.py`
- `tools/learning/test_cell_split.py`
- `tools/learning/test_finetune_runner.py`
- `core/STATE/MODEL_DNA.md`
- `core/benchmarks/learning_controller.md`
- `core/BUILD/signals/weighting_directive.json`
- `core/BUILD/specs/SPEC_d093_continuous-learning-controller-c.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added the d093 controller layer on top of the d086 learning scaffold:

- Unified learning signal ingestion for correction, approval, reversal,
  merge-outcome, engagement, and council-verdict rows.
- Brain-index schema for `learning_signals`, `model_directives`, and
  `model_versions`.
- Deterministic council guidance that emits a `weighting_directive.json`.
- Fine-tune planning extended to require `LEARNING_ENABLED=1`, 100 signals,
  dataset/correction gates, a directive, d073 benchmarks, `FINETUNE_APPROVED=1`,
  `HAS_GPU=1`, and RunPod monthly budget projection within $50.
- Weighted prompt/response corpus construction from captured signals.
- Cell split exporter that copies canonical `MODEL_DNA` only and deletes the
  generated template if personal markers are detected.
- Living `core/STATE/MODEL_DNA.md` defining transferable canonical DNA and
  non-transferable personal DNA.

## Tests

- `python3 -B -m unittest tools.learning.test_controller tools.learning.test_council_guidance tools.learning.test_cell_split tools.learning.test_dataset_builder tools.learning.test_finetune_runner` — 20 passed.
- `python3 -B -m tools.learning.council_guidance --output core/BUILD/signals/weighting_directive.json`
- `python3 -B -m tools.learning.finetune_runner --notice /tmp/d093_ready_notice.json` — correctly blocked by gates.
- `python3 -B -m tools.learning.cell_split d093-smoke --output-root /tmp/d093-cell-split-final --approve-for-test` — generated a test template with `leaks: []`.

## Risks

- The live proof still requires a real `brain_index` migration and 100+
  production-quality learning signals.
- The fine-tune runner still does not execute RunPod training or Ollama swaps;
  it produces a gated activation plan only.
- The cell split proof here is test-only under `/tmp`; live exports still need
  explicit per-export approval with `CELL_SPLIT_APPROVED=1`.

## Rollback

Revert the listed files and delete generated local artifacts under
`/opt/fpai-build/learning_datasets/` or `/tmp/d093-cell-split` if present. Keep
`LEARNING_ENABLED`, `FINETUNE_APPROVED`, and `CELL_SPLIT_APPROVED` unset to
block all live activation paths.

## Intent Solved

The continuous learning loop now has a concrete controller surface: captured
signals, council weighting, gated fine-tune planning, model DNA, and clean
cell-split export checks.

## Downstream Intent Unlocked

After migration and 100 real signals, Ember can run a no-training readiness pass
that shows exactly what remains before asking James for the first fine-tune or
first approved cell split.
