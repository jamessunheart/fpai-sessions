---
type: spec
status: queued (scout-adopted · AUTO)
source: AI GROWTH FEED · 2026-05-31
---

# Adopt: "Obsidian Memory for AI" pattern

**Rubric:** score 14/15 · verdict AUTO

**Why:** it's a near-exact description of Ember's `memory/` design — external validation, plus the *materialized-view* idea (generate read-model files from raw facts) is something we don't do yet.

**Proposed use:** add a generated "index/digest" view layer over `memory/`.

**Source:** https://github.com/jrcruciani/obsidian-memory-for-ai

**Definition of done:** evaluate + integrate (or prototype) the proposed use; reversible; proof in [[PROOF LOG]].
**Who:** Codex (build) / AI(Ember) (light integration). One spec = one branch.
