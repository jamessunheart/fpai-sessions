# AI Review — build/SPEC_d086_glm-5-2-fine-tune-pipeline-conti

**Verdict:** APPROVE · **Risk:** low

**Summary:** d086 adds a gated continuous-learning scaffold (dataset builder + non-executing fine-tune runner) on feat/headless-build; no training, money, prod writes, secrets, push, or merge — safe to merge.

## Findings
- Non-blocking: --from-live-db reads brain_index (corrections/tg_messages/probe_sessions) but is SELECT-only, opt-in, and requires a DSN env var — no writes to memory/prod, no secrets printed.
- Non-blocking: load_live_brain_index hardcodes a brain_index schema (corrections.conversation_id/bot_turn_id, tg_messages.chat_id/role/at); on schema mismatch the opt-in path raises uncaught and aborts the run. No data corruption risk, but verify schema before live export.
- Non-blocking: exported JSONL contains James's private corrections, but defaults outside the repo (/opt/fpai-build/learning_datasets/) and this build never runs the export, so nothing private enters git.
- Non-blocking: finetune_runner is fully gated (FINETUNE_APPROVED=1 + HAS_GPU=1 + d073 benchmarks + --execute) and even when all gates pass returns training_adapter_not_implemented — it cannot actually train, correctly deferring live GPU work to a separate review.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
