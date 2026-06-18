# AI Review — build/SPEC_d087_pma-membership-terms-council-rev

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds a draft PMA membership terms doc, a deterministic council-review memo, a Python phrase/marker guard with passing tests, and a pre-launch reconciliation gate — all repo-only, additive, and explicitly counsel-gated; safe to merge.

## Findings
- No code or security defects: pma_terms_guard.py only reads two in-repo files and runs regex marker checks; REPO_ROOT (parents[2]) resolves correctly and the `compounding utility value` negative-lookahead correctly whitelists the doc's own quoted usage.
- No boundary crossings: no money movement, no prod server (162/198/209) writes, no identity/memory/secrets, not on main, and Codex correctly left status='done' without setting 'merged' (Ember-only). PATRON_ENGINE.md change is a single additive checklist line that strengthens, not bypasses, a gate.
- Slightly beyond literal spec (spec asked for terms + council review; build also added a guard tool, tests, and reconciliation gate) but all additions are supportive and low-risk, not scope creep with side effects.
- Non-blocking: this is AI-drafted legal language for a real money-bearing structure (Patron Engine→Treasury). The repeated disclaimers (draft only, not legal advice, gated on counsel + James, no checkout/launch) are present and appropriate — do not publish or activate until qualified counsel signs off.
- Process note: the build's own independent `claude -p` review was blocked (API ConnectionRefused) and untracked files were invisible to the branch diff until staged; this human/independent review now covers it, but Ember should stage/commit and confirm the full file set before merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
