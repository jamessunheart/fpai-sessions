# Learning Controller Benchmark

Tracks the continuous learning controller from d086. This surface is read-only
until the gates below pass; it is not approval to train or deploy a model.

## Gates

| Gate | Requirement | Current source |
|---|---|---|
| 1 | `brain_index.corrections` has at least 50 rows | `tools/learning/dataset_builder.py` export gate |
| 2 | d073 per-agent benchmarks are live | `core/benchmarks/per_agent_scores.jsonl` |
| 3 | James explicitly approves first fine-tune | `FINETUNE_APPROVED=1` |
| 4 | GPU host is available | `HAS_GPU=1` or queued ready-to-train notice |

## Metrics To Track

| Metric | Source | Notes |
|---|---|---|
| Dataset examples | exported JSONL row count | Defaults outside the repo at `/opt/fpai-build/learning_datasets/glm52_training.jsonl` |
| Correction pairs | `brain_index.corrections` | DPO: corrected response chosen over original |
| Approved build patterns | ops ledger merge outcomes | SFT: spec/context to good build pattern |
| Probe quality examples | `brain_index.probe_sessions.quality_score` | High-quality sessions become positive examples |
| Last fine-tune date | adapter metadata | Must remain blank until James approval |
| Before/after quality | d073 benchmark score deltas | Compare agent scores before and after adapter eval |

## Current Posture

- Dataset builder can export once the correction/example gates pass.
- Fine-tune runner is a scaffold: it writes readiness notices and blocks training
  unless `FINETUNE_APPROVED=1`, d073 scores exist, and `HAS_GPU=1`.
- Adapter target: `/opt/fpai-build/models/glm-5.2-fpai-lora/`.
- LoRA config: rank 16, target modules `q_proj` and `v_proj`, epochs 3.

## Rollback

Delete the exported JSONL/notice files under `/opt/fpai-build/learning_datasets/`
and do not set `FINETUNE_APPROVED=1`. If adapter weights are later produced after
approval, remove the adapter directory and route model selection back to the
previous base.
