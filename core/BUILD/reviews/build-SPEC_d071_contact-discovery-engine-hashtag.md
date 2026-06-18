# AI Review — build/SPEC_d071_contact-discovery-engine-hashtag

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds dry-run-first public contact discovery (Reddit/X/IG/Telegram/HN/GitHub) feeding probe_pool; safe by default (DISCOVERY_LIVE gate, master+per-source kills, score gate, Telegram DM gate, no push/merge, branch off feat/headless-build) but live use is cold-outreach + web scraping that warrants care.

## Findings
- Reddit karma filter is effectively a no-op: public new.json has no author_karma/author_total_karma fields, so karma defaults to 11 and the 'karma>10 filters bots' requirement never actually filters. Fails open (less filtering), low impact but defeats spec intent.
- migrate_discovery_columns.sql DROPs and re-ADDs the live probe_pool platform CHECK constraint. Additive (expands allowed platforms) and manual-apply only, but it mutates an existing constraint on a live brain_index table — verify on 162 before running; not auto-applied.
- Migration sets discovery_score DEFAULT 0.5, so all pre-existing probe_pool rows now pass the new >=0.4 outreach gate. Confirm this is intended and won't surface previously-out-of-scope contacts.
- Twitter/X and Instagram are scraped via Playwright on public pages — ToS-fragile, rate-limit prone, and a reputational/legal surface for cold outreach. Spec acknowledges; keep dry-run until James blesses a tiny live batch and the STOP/30-day-recontact governor is confirmed working.
- Diff truncated at 60k: the most safety-critical changes (tools/probe/agent.py send-gating, twitter_crawler.py, email_adapter.py) are not visible here. The Telegram-DM gate (TELETHON_DM_ENABLED) and >=0.4 score enforcement live in those files and were only verified by the prior subagent review — confirm those gates directly before any DISCOVERY_LIVE=1 run.
- SQL uses parameterized queries with a fixed column allowlist (no injection); no secrets/identity/memory/treasury touched and no auto-merge in this diff. Good guardrail posture.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
