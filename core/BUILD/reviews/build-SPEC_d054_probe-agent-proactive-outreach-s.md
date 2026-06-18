# AI Review — build/SPEC_d054_probe-agent-proactive-outreach-s

**Verdict:** APPROVE · **Risk:** med

**Summary:** Probe Agent: self-governed outbound outreach to James-seeded contacts via Telegram, with rate governor, kill switches, parameterized SQL, and review-only schema/timer — safe in committed state (nothing sends until James manually installs + sets token + seeds pool); not on main, no secrets, no money/prod writes.

## Findings
- Capability note (not a blocker): once James installs the systemd timer + schema + TELEGRAM_BOT_TOKEN and seeds probe_pool, the 10:00 UTC cycle sends to real people autonomously without per-message approval. Bounded by START_RATE=3, MAX_RATE=50, pool-promotion gates (warm→adjacent→cold each need >60% completion), PROBE_DISABLE=1, and /opt/fpai-build/.probe_disabled. Verify these gates before first live proof.
- Fails closed correctly: default_send returns False if Hermes/token absent; rate_governor returns 0 on smoke_fail (6h), >5 corrections/day, <30% completion, or db_unavailable; digest/scanner probe queries are try/except-guarded so a missing table won't break those live services.
- Persistence-before-send confirmed: record_probe_session + mark_probed run before sender(), so no untracked sends; 30-day no-recontact enforced via last_probed_at. Sends use James-seeded handle directly (loose tg_messages handle-matching is only for outcome attribution, not send targeting — no misdirected-send risk).
- SQL is parameterized throughout; dynamic column names in refresh_session_outcomes are intersected against a fixed allowlist from information_schema — no injection. Reads VOICE.md and tg_messages read-only; writes only its own new probe_pool/probe_sessions tables — does not mutate existing memory.
- Avoids the d051 trap: curator digest.py does its probe query inline and does NOT import tools.probe, so no sys.path shadowing reintroduced into the live service. Minor: signals.py (format_morning_digest_section, horizon_probe_flags) appears unused by digest.py/scanner.py which reimplement inline — partial dead code, cleanliness only.
- Live-proof prerequisites to verify before enabling: (a) probe_pool.handle must be a numeric Telegram chat_id or a user with prior bot interaction — bots cannot DM arbitrary @usernames, so cold sends will fail-closed (ok=false), which is acceptable but means cold outreach is effectively inert until handles are valid; (b) apply tools/probe/schema.sql to brain_index manually. Diff was truncated at 60k chars (signals.py horizon_probe_flags and test_probe.py not fully visible) — recommend a glance at remaining test coverage, though all safety-critical files were fully reviewed.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
