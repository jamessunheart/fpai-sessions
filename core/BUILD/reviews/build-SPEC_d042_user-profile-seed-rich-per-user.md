# AI Review — build/SPEC_d042_user-profile-seed-rich-per-user

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Well-gated per-user profile layer with good namespace isolation, but modifies the live owner chat path on prod (162) with an unverified _log_tg_message(private_flag=...) signature and a hardcoded default DB password.

## Findings
- LIVE-PATH RISK: tgbot.py now calls _log_tg_message(..., private_flag=not is_owner) for ALL users including the owner/James, but the diff never shows _log_tg_message gaining a private_flag parameter. py_compile and the string-matching wiring tests would NOT catch a bad kwarg. If the live function on server 162 lacks this param, every message log (including James's) raises TypeError. Confirm _log_tg_message accepts private_flag before merge.
- HARDCODED DEFAULT CREDENTIAL: migrate_add_user_profiles.py defaults DB_URL to 'postgres://brain_index:changeme@127.0.0.1:25432/appflowy'. Placeholder password 'changeme' baked as fallback; prefer requiring BRAIN_INDEX_DB_URL or failing loudly rather than a guessable default.
- AUTH MODEL: chat access for non-owners is granted solely by the existence of a brain_index.user_profiles row (is_profile_user). No profile-creation path exists yet (d036 flow.py absent), so the path is currently unreachable — but once seed_profile is wired, anyone with a seeded row gets full conversational access. Ensure seeding is authenticated/owner-controlled.
- TEAM-CAPTURE BYPASS: guard changed from `if not is_owner:` to `if not is_owner and not is_profile_user:`. A TEAM_CAPTURE user who later gains a profile would skip the Linear team-capture flow and fall through to chat. Edge case today (no profiles exist) but a latent regression in capture routing.
- PRODUCTION DB: migration creates brain_index.user_profiles on the live Postgres when run. It is idempotent and FK-gated, and was not executed in-sandbox per the result file — verify it is run deliberately, not auto-applied, and back up first.
- PROMPT INJECTION (low): user onboarding answers and proof_text are passed into `claude -p` for extraction; deterministic fallbacks limit impact, but extracted fields flow into the user's system prompt context. Acceptable but worth noting.
- MINOR: get_agent_context bounds output by word count (_limit_tokens splits on whitespace) but labels it tokens/200-token max — actual token count can exceed 200. Not a safety issue.
- POSITIVE: profile users never search James's brain (hits=[] when not owner), get a separate USER_CHAT_SYSTEM_PROMPT, are excluded from correction capture, blocked from slash commands, and namespace isolation is unit-tested. Off main, branched on feat/headless-build, $0 CLI path. No treasury/secrets/identity-stack changes.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
