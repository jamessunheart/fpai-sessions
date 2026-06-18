# AI Review — build/SPEC_d081_becoming-engine-v1-per-person-jo

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds advisory per-person Becoming Engine v1 (SEE model) — new brain_index.becoming table, deterministic stage/intent inference, bounded prompt injection, best-effort Telegram capture; reversible, non-sending, parameterized SQL, branched off feat/headless-build not main.

## Findings
- Public-lane expansion: capture + same-person becoming context now run on the public answer path, and the public prompt loosens from 'use only the public context pack' to 'you may also use the same-person becoming context.' Becoming state is keyed by person_id=chat_id so no cross-person leak (each public user sees only their own derived data, James's owner state stays under his own chat_id), but this widens what the public lane surfaces — review under the existing public/private canary posture before public mode is broadened, as the build's own result.md flags.
- Public-lane PII collection: every public message now persists the user's clipped message text (proofs.signals), stated intent, blocker, and Telegram username/first/last name into brain_index.becoming. Within spec's design but is new data collection on non-owner humans — confirm this is acceptable for public users.
- Latency: in _synthesize_public_answer the capture awaits a DB read+write inline BEFORE generating the answer. It's try/except-wrapped so it never fails the answer, but it serializes a round-trip onto every public reply; the private path correctly runs capture after the answer. Consider fire-and-forget for the public path.
- schema.sql adds unqualified `becoming` while migration/code use `brain_index.becoming` — consistent with the existing `corrections` table pattern (search_path=brain_index assumed), so fine, just verify the brain-index host applies it under that schema.
- Reversibility confirmed: SH_BECOMING_CONTEXT_DISABLE=1 disables injection, migration unapplied disables persistence, table is droppable — good guardrails.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
