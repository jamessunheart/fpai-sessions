---
type: spec
status: queued (scout-adopted · TAP)
source: AI GROWTH FEED · 2026-05-31
---

# Adopt: Microsoft Conductor

**Rubric:** score 12/15 · verdict TAP

**Why:** our Workflow/agent fan-outs pay tokens for control flow that's actually deterministic; a YAML-declared, diffable pipeline is cheaper and more auditable.

**Proposed use:** prototype one recurring fan-out (e.g. the scout itself) as a Conductor YAML and compare cost.

**Source:** https://opensource.microsoft.com/blog/2026/05/14/conductor-deterministic-orchestration-for-multi-agent-ai-workflows/

**Definition of done:** evaluate + integrate (or prototype) the proposed use; reversible; proof in [[PROOF LOG]].
**Who:** Codex (build) / AI(Ember) (light integration). One spec = one branch.
