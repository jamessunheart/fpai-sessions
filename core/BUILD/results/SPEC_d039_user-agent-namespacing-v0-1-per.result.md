# SPEC_d039_user-agent-namespacing-v0-1-per Result

Status: done / awaiting James review + merge review

Summary:
- Added `brain_index.user_agents` migration/schema support and a guarded `brain_index.thread(user_id)` path.
- Added `curator.agent` with `UserAgent`, in-memory/Postgres stores, capability registry, and operator boundary helpers.
- Patched Telegram dispatch so operator behavior remains unchanged, mapped tenants get isolated context/rate limits, tenant turns log to `brain_index.thread` instead of the James capture buffer, and unmapped public onboarding is closed unless `MULTIUSER_OPEN_ONBOARDING=1`.
- Patched the continuity thread loader so James/Ember recent context only reads `user_id='james'`.

Tests:
- `PYTHONPATH=SERVICES/sunheart-brain python3 -B -m unittest curator.agent.test_user_agent`
- `python3 -B SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `python3 -B SERVICES/sunheart-brain/curator/test_tgbot_user_agent_wiring.py`
- `python3 -B tools/continuity/test_thread_namespacing.py`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/agent/__init__.py SERVICES/sunheart-brain/curator/agent/operator.py SERVICES/sunheart-brain/curator/agent/capability_registry.py SERVICES/sunheart-brain/curator/agent/user_agent.py SERVICES/sunheart-brain/curator/agent/test_user_agent.py SERVICES/sunheart-brain/curator/test_tgbot_user_agent_wiring.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/telegram.py tools/db/migrate_add_user_agents.py tools/continuity/thread.py tools/continuity/test_thread_namespacing.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check -- SERVICES/sunheart-brain/curator/agent SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/telegram.py SERVICES/sunheart-brain/index/schema.sql tools/db/migrate_add_user_agents.py tools/continuity/thread.py tools/continuity/test_thread_namespacing.py core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d039_user-agent-namespacing-v0-1-per.md`

Independent review:
- Completed by subagent. Initial blockers found tenant leakage through `tg_messages`, owner-targeted capture notifications, public fallback LLM access, and then global `thread.py recent` leakage. All were fixed. Final review reported no remaining blockers.

Risks:
- Migration was not run against live Postgres in this sandbox.
- Live Telegram and live Hermes/user_channels integration were not exercised.
- Tenant voice remains closed in v0.1 because the legacy voice path uses owner-oriented send helpers.

Rollback:
- Revert the changed files.
- Runtime kill switch: set `MULTIUSER_DISABLE=1` to preserve current James-only behavior.
- If the migration was applied and the branch is abandoned, leave `brain_index.user_agents` harmlessly unused or drop it manually only after confirming no tenant rows are needed.

Intent solved:
- Hermes-routed users can have isolated agent records, capabilities, rate limits, and tenant-local conversation context without exposing James's memory.

Downstream intent unlocked:
- User-facing onboarding/agent flows can now build on a tenant namespace instead of the previous James-only substrate.
