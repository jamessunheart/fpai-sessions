# AI Review — build/SPEC_d080_contact-pre-profiler-research-pu

**Verdict:** APPROVE · **Risk:** low

**Summary:** New-files-only public-source contact pre-profiler with SSRF guards, privacy redaction, and no live sends/deploys/merges — in scope and safe; minor non-blocking gap is the rate-limiter not being enforced on the library code path.

## Findings
- Rate limiter (guardrail: max 5 fetches/min) is only wired into the CLI main() path via a lambda; the library paths (collect_sources/build_profile/profile_and_store/seed_and_profile) call fetch_public_source with no limiter, so the respectful-crawl cap is not enforced when invoked programmatically. Low impact today because default_searcher is a no-op and only a handful of url_hints are fetched, but should be wired before any live search adapter lands.
- SSRF defense has a residual DNS-rebind TOCTOU window: host_resolves_public() resolves the host, then urllib resolves again at fetch time. Acceptable given redirects are disabled and is_global is checked, but note it before exposing the seed endpoint publicly.
- Standalone /api/contacts/seed router is intentionally unmounted and send_status is hard-coded 'not_sent' — no live sends, no deploy, no push/merge. Migration is a static .sql file (not auto-applied). All within spec.
- No secrets, money, prod-server, identity, or main-branch contact. Sensitive-content (health/family/financial) redaction and PRIVATE-tier CHECK constraint are present and tested.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
