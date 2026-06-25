# Learning Controller Benchmark

Tracks the continuous learning controller from d086 and d093. This surface is
read-only until the gates below pass; it is not approval to train, deploy,
change Ollama routing, or export a person-specific template.

## Gates

| Gate | Requirement | Current source |
|---|---|---|
| 1 | `brain_index.learning_signals` has at least 100 rows | `tools/learning/controller.py` |
| 2 | `brain_index.corrections` has at least 50 rows and dataset has at least 50 examples | `tools/learning/dataset_builder.py` export gate |
| 3 | Council weighting directive exists | `tools/learning/council_guidance.py` |
| 4 | d073 per-agent benchmarks are live | `core/benchmarks/per_agent_scores.jsonl` |
| 5 | James explicitly approves first fine-tune | `FINETUNE_APPROVED=1` |
| 6 | GPU host is available | `HAS_GPU=1` or queued ready-to-train notice |
| 7 | RunPod training stays under $50/month projection | `RUNPOD_BUDGET_MONTHLY_USD` / `RUNPOD_PROJECTED_MONTHLY_USD` |
| 8 | Cell split export is explicitly approved per template | `CELL_SPLIT_APPROVED=1` |

## Metrics To Track

| Metric | Source | Notes |
|---|---|---|
| Learning signals | `brain_index.learning_signals` or local JSONL fallback | Unified correction/approval/reversal/merge/engagement/council signal count |
| Weighting directive | `core/BUILD/signals/weighting_directive.json` | Council guidance for the next learning cycle |
| Dataset examples | exported JSONL row count | Defaults outside the repo at `/opt/fpai-build/learning_datasets/glm52_training.jsonl` |
| Correction pairs | `brain_index.corrections` | DPO: corrected response chosen over original |
| Approved build patterns | ops ledger merge outcomes | SFT: spec/context to good build pattern |
| Probe quality examples | `brain_index.probe_sessions.quality_score` | High-quality sessions become positive examples |
| Weighted corpus rows | `tools/learning/finetune_runner.py` | Prompt/response/weight triplets after directive application |
| Last fine-tune date | adapter metadata | Must remain blank until James approval |
| Before/after quality | d073 benchmark score deltas | Compare agent scores before and after adapter eval |
| Cell split leaks | `tools/learning/cell_split.py` scan result | Must be zero before any template is used |

## Current Posture

- Dataset builder can export once the correction/example gates pass.
- Learning controller captures unified signals to `brain_index.learning_signals`
  when a live connection exists, or to a local JSONL proof ledger when it does
  not.
- Council guidance generates a deterministic weighting directive for the next
  learning cycle.
- Fine-tune runner is a scaffold: it writes readiness notices and blocks training
  unless learning is enabled, 100 signals exist, the directive and dataset gates
  pass, d073 scores exist, `FINETUNE_APPROVED=1`, `HAS_GPU=1`, and RunPod budget
  projection is within $50/month.
- Adapter target: `/opt/fpai-build/models/glm-5.2-fpai-lora/`.
- LoRA config: rank 16, target modules `q_proj` and `v_proj`, epochs 3.
- Cell split exports only canonical `core/STATE/MODEL_DNA.md`, a README, a
  manifest, and example config. It blocks without `CELL_SPLIT_APPROVED=1` and
  deletes the template if personal markers are detected.

## Rollback

Delete the exported JSONL/notice files under `/opt/fpai-build/learning_datasets/`
and do not set `FINETUNE_APPROVED=1`. If adapter weights are later produced after
approval, remove the adapter directory and route model selection back to the
previous base. Delete any generated `dist/fpos_template_*` directory if a
cell-split export is later approved and then reversed.
