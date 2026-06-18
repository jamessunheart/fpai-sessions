# AI Review — build/SPEC_d038_content-bank-v0-1-truth-asset-sc

**Verdict:** APPROVE · **Risk:** low

**Summary:** Draft-only content bank plus well-tested helper scripts; contained, kill-switched, skips existing files — no real risk surface.

## Findings
- All 7 assets are draft-tagged and explicitly review-only; seed_content_bank skips any existing file so James-edited content is never overwritten — idempotent and safe.
- Branched off feat/headless-build (not main), registered in REGISTRY.json, 9 tests pass. No secrets, no credential or treasury access, no identity/memory mutation.
- subprocess calls use list-args (no shell=True); claude -p runs on flat-rate subscription ($0) with a deterministic fallback if CLI absent. No injection surface.
- Live-path side effects are real but low-impact: appends one row to /opt/fpai-build/ops_ledger.jsonl and best-effort fires notify_telegram.sh. Both are wrapped in try/except and gated by CONTENT_BANK_DISABLE=1.
- CORA/Fi-Art copy is legally sensitive; it carries containment language and is draft-tagged, but must stay review-only until James/compliance approve amounts, redemption, and claims before any public use.
- Mild scope note: variant_generator.py is created here though the spec frames it as wiring into d037 (not yet built) — acceptable as a standalone source-remix module, not a modification of nonexistent d037 code.
- throttle.cora_farming_guard handles zero-proof/zero-earned edge cases correctly (inf ratio when earned>0 & proofs==0; ratio 0 when both zero).

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
