# AI Review — build/SPEC_d098_cognee-graph-memory-layer

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds an additive, idempotent graph-memory layer (3 new brain_index tables + curator sync/query module) over existing probe/becoming/corrections rows; read-only on existing data, not pushed/merged, off feat/headless-build — safe.

## Findings
- Advisory (not blocking): live becoming join may silently return empty. load_contact_rows selects no person_id column, so person_id falls back to the synthesized key 'person:telegram:<handle>', and the becoming query filters on that same synthesized key. If the live brain_index.becoming.person_id is stored in a different format, stage edges will be absent at runtime even though tests pass with hand-crafted fixtures that match the key format. Verify against real rows during the gated live proof.
- Advisory: schema.sql additions touch the live memory DB (brain_index). They are CREATE TABLE/INDEX IF NOT EXISTS only (additive, no ALTER/DROP on existing tables), so low risk — but applying schema to the memory substrate on 162 should be done by Ember's hand, not auto-applied. Result doc correctly states no live sync was run.
- Minor dead code: PROOF_NODE_PREFIX is defined but unused; correction nodes are created but never linked by any edge to people/proofs, so they are orphan nodes with no traversal value yet.
- Minor: SHARES_INTEREST_WITH builds O(n^2) edges per topic, harmless at DEFAULT_CONTACT_LIMIT=10 but would grow quadratically if the limit is raised — worth a cap before scaling.
- No security issues: all SQL is parameterized, writes are confined to the new graph_memory_* tables, no secrets/money/identity/prod-loop/main-branch surface touched.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
