# AI Review — build/SPEC_d066_public-private-data-lane-protoco

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds a structural public/private data-lane partition (curated public context pack + canary probe + bot mode gate) to the live Telegram bot; safe by default — public replies stay disabled until James sets PUBLIC_MODE_CONFIRMED=1, partition is fail-closed and reads no private tables.

## Findings
- Public answer path (_synthesize_public_answer) calls llm.complete on every non-canary public message with no rate limiting — if James enables PUBLIC_MODE_CONFIRMED a public bot could be spammed and drive token cost; recommend a per-chat rate limit / daily cap before going live, and confirm complete() routes through the subscription CLI not a metered API (cost-cap rule).
- The canary probe only exercises the deterministic regex denial path: all 7 canary questions match the private_probe regex in _synthesize_public_answer and short-circuit to public_denial() before the LLM, so the probe validates the blocklist but never tests the LLM answer path against the actual public context pack. Structural partition (pack reads no private tables) is the real defense and is sound, but the canary gives weaker assurance than it appears — HANDOFF acknowledges this.
- Regex private_probe is a blocklist (belt-and-suspenders); it can miss novel phrasings, but the partition makes this non-blocking. Fine as a secondary layer.
- Migration tools/privacy/migrate_public_ok.sql targets the live brain_index.decisions table on server 162 — it is idempotent (ADD COLUMN IF NOT EXISTS, default false) and NOT auto-applied by this build; James must run it manually. Verify it is applied before public mode is enabled, otherwise the public_ok query errors (caught and fails closed to no decisions, which is safe).
- Owner-in-a-group is now treated as public (is_private_james requires chat_type=='private'), a tightening of access — intended and correct.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
