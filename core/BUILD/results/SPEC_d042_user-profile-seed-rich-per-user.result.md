# SPEC_d042_user-profile-seed-rich-per-user Result

Status: done / awaiting James review + merge review

## Summary

Added the user-profile seed layer for per-user agent context:

- `tools/db/migrate_add_user_profiles.py` creates `brain_index.user_profiles` idempotently and adds the `user_agents` foreign key only when the d039 parent table exists.
- `SERVICES/sunheart-brain/curator/agent/profile.py` provides `seed_profile`, `update_profile_from_session`, `get_agent_context`, `extract_strength_from_proof`, and `profile_exists`.
- `SERVICES/sunheart-brain/curator/tgbot.py` now preserves James sessions unchanged while adding a profile-authorized non-operator path that uses compact user context, blocks James brain search, blocks non-owner slash commands, skips James correction capture, and logs non-owner turns as private.
- Focused tests cover required profile fields, 200-token context bound, streak updates, strength appends, namespace isolation, and tgbot wiring guards.

## Tests

- `python3 -B -m unittest SERVICES/sunheart-brain/curator/test_corrections.py SERVICES/sunheart-brain/curator/test_build_context.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py SERVICES/sunheart-brain/curator/agent/test_profile.py` — 18 tests OK.
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/db/migrate_add_user_profiles.py SERVICES/sunheart-brain/curator/agent/profile.py SERVICES/sunheart-brain/curator/agent/test_profile.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`.
- `python3 -m json.tool core/BUILD/REGISTRY.json`.
- `git diff --check -- SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py SERVICES/sunheart-brain/curator/agent/profile.py SERVICES/sunheart-brain/curator/agent/test_profile.py tools/db/migrate_add_user_profiles.py core/BUILD/REGISTRY.json`.

## Independent Review

Completed by subagent. First pass found the profile path was unreachable for non-owner users and could have searched James/global brain if opened. Fixed by gating non-operator chat on `profile_exists`, using `actor_user_id` consistently, setting non-owner hits to `[]`, adding `USER_CHAT_SYSTEM_PROMPT`, owner-gating correction capture, blocking non-owner slash commands, marking non-owner logs private, and propagating profile write failures.

Remaining review caveat: the spec says d036 onboarding `flow.py` step 5 should call `seed_profile`, but no `flow.py` or d036 onboarding artifact exists in this checkout. `seed_profile` is ready, but the exact call-site must be wired when that flow is present.

## Risks

- Live DB migration was not executed in this sandbox.
- Live `claude -p` extraction was not exercised; deterministic fallbacks keep tests and local behavior stable.
- The d036 onboarding hook is not wired because the target flow file is absent from this branch.
- Non-operator Telegram chat now depends on an existing `brain_index.user_profiles` row; unknown strangers remain blocked.

## Rollback

Revert:

- `tools/db/migrate_add_user_profiles.py`
- `SERVICES/sunheart-brain/curator/agent/`
- the d042 additions in `SERVICES/sunheart-brain/curator/tgbot.py`
- the d042 assertions in `SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- the d042 row in `core/BUILD/REGISTRY.json`
- this result file and the HANDOFF entry

If the migration was applied live and the branch is abandoned before real profile data exists, drop `brain_index.user_profiles`.

## Intent

Intent solved: user sessions now have a durable per-user profile substrate and compact prompt context path instead of relying on James/global context.

Downstream intent unlocked: CORA, subscriptions, matching, and capability grants can read one profile namespace per user once d036 onboarding writes the first row.
