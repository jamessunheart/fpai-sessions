# AI Review — build/SPEC_d113_auto-seed-orphaned-spec-files-bu

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Adds a build-loop preflight that auto-seeds orphaned SPEC_dNNN files as 'answered' needs_build=true decisions in the live brain_index.decisions DB — works and is tested, but inverts the human-approval gate so any spec file dropped on disk becomes an auto-approved autonomous build.

## Findings
- Approval-gate inversion: normal flow is James-answers→decision→spec→build. This reverses it (spec file→auto-'answered' decision→build) with answer literally 'auto-seeded from orphaned spec file' and no human approval. Any SPEC_dNNN written by another Claude session, the forge, or a bad merge now becomes an auto-queued autonomous build. Recommend seeding as a non-build/needs-review state (not status='answered', needs_build=true) or requiring linkage to a real answered decision.
- Unbounded first-run fan-out: with d101–d112 already sitting as committed specs, the first live run could seed up to a dozen rows at once and trigger a burst of autonomous builds with no batch cap or per-run limit — only a print() of seeded ids. Add a cap and explicit log of count/cost.
- Writes to live brain_index.decisions (brain memory/prod on server 162) but was never exercised against the live DB; column set (build_status, spec_written, explicit text id 'dNNN') and id conflict target are unverified assumptions. Non-fatal `|| true` swallows failures silently, so a schema mismatch would be invisible beyond stderr.
- Minor: hardcoded default credential string in source (postgres://brain_index:changeme@127.0.0.1:25432/appflowy) — localhost-only and env-overridable, but avoid committing placeholder creds; require BRAIN_INDEX_DB_URL to be set.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
