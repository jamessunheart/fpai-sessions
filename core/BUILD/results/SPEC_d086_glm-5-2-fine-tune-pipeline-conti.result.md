# SPEC_d086_glm-5-2-fine-tune-pipeline-conti Result

- Status: done in working tree / independently AI-reviewed / awaiting merge review
- Branch: `build/SPEC_d086_glm-5-2-fine-tune-pipeline-conti`
- Base: `feat/headless-build`

## Files Changed

- `tools/learning/__init__.py`
- `tools/learning/dataset_builder.py`
- `tools/learning/finetune_runner.py`
- `tools/learning/test_dataset_builder.py`
- `tools/learning/test_finetune_runner.py`
- `core/benchmarks/learning_controller.md`
- `core/BUILD/specs/SPEC_d086_glm-5-2-fine-tune-pipeline-conti.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d086_glm-5-2-fine-tune-pipeline-conti.result.md`
- `docs/codex/HANDOFF.md`

## Summary

Added the continuous learning controller scaffold for GLM-5.2. The dataset
builder exports HuggingFace-style chat JSONL from three learning signals:
James corrections as DPO pairs, approved merge outcomes as SFT build-pattern
examples, and high/low probe-session quality examples when populated.

Dataset export refuses to write until both gates pass: at least 50 correction
rows and at least 50 total examples. Generated private datasets and ready
notices default outside the repo at `/opt/fpai-build/learning_datasets/`.
The optional live DB reader joins correction rows back to the previous user turn
from `brain_index.tg_messages` when available; if no context exists, it uses a
generic prompt instead of leaking internal conversation IDs into user content.

The fine-tune runner is a gated scaffold for GLM-5.2 LoRA with rank 16,
`q_proj`/`v_proj`, and 3 epochs. It requires dataset size/correction gates, d073
benchmark scores, `FINETUNE_APPROVED=1`, `HAS_GPU=1`, and `--execute`; without
`--execute` it reports `ready_requires_execute` and `will_train=false`.

## Tests

- `python3 -B -m unittest tools.learn.test_capture_corrections tools.learn.test_learn tools.learning.test_dataset_builder tools.learning.test_finetune_runner` (16 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/learning/__init__.py tools/learning/dataset_builder.py tools/learning/finetune_runner.py tools/learning/test_dataset_builder.py tools/learning/test_finetune_runner.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d086-registry.json`
- `git diff --check`
- CLI smoke: dataset builder exported 50 correction DPO rows to `/tmp/.../out.jsonl`
- CLI smoke: fine-tune runner with 50 correction rows + benchmark fixture + approval/GPU env returned `ready_requires_execute` and `will_train=false`

## Independent Review

Initial review found P2 issues: private generated datasets defaulted inside the
repo, live correction prompts could fall back to internal conversation IDs, and
the runner could mark a one-row dataset ready. Fixes landed for all three.
Final blocker-only re-review found no remaining P1/P2 blockers.

## Risks

No training, GPU job, model download, deploy, secret access, push, or merge was
performed. The training execution path remains a reviewed scaffold, not a live
Unsloth/PEFT implementation. Live DB export depends on the actual
`brain_index.tg_messages` schema being available for best prompt context.

## Rollback

Revert the d086 files listed above. Delete any generated files under
`/opt/fpai-build/learning_datasets/` if a live export was run later. Leave
`FINETUNE_APPROVED` unset and remove any future adapter directory at
`/opt/fpai-build/models/glm-5.2-fpai-lora/` if training is later approved and
needs rollback.

## Intent Solved

The learning controller now has a concrete, guarded dataset/export target for
James's corrections, build outcomes, and future probe quality signals.

## Downstream Intent Unlocked

Once the correction count and d073 benchmark gates are live, Ember can run a
dry export and present James with a concrete first-fine-tune approval gate
instead of building the pipeline after the data is ready.

