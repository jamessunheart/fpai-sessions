# AI Review — build/SPEC_d039_user-agent-namespacing-v0-1-per

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Solid tenant isolation, but multi-tenant defaults ON on the live James bot and silently regresses team-capture for unmapped users.

## Findings
- Default-on risk: multi-tenant routing is enabled by default — the new `if not is_owner:` tenant branch runs unless MULTIUSER_DISABLE=1 is explicitly set. For a feature this sensitive on the live production bot (server 162), the safe default should be OFF (opt-in via MULTIUSER_ENABLE), not opt-out via a kill switch.
- Team-capture regression: previously non-owner team users (TEAM_CAPTURE_USERS / _is_team_capture_user) were handled by the old non-owner block; now with multiuser enabled they fall into the tenant branch and, if they have no brain_index.user_channels mapping, get rejected with 'not open for onboarding' instead of being captured. This silently changes live behavior for existing authorized team members. is_team/capture_name are computed but no longer consulted on the tenant path.
- Guardrail/gate change in telegram.send(): the old `enabled()` check was replaced with an inline `BOT_TOKEN and target_chat_id` test. If enabled() encapsulated any additional disable/kill logic, this is a silent bypass. send() can now target an arbitrary chat_id — confirm callers cannot be induced to send to a chat_id other than the resolved tenant's own.
- No guard preventing a tenant from resolving to user_id='james': _resolve_user_id trusts whatever brain_index.user_channels returns; a bad/poisoned mapping row would hand a tenant the operator namespace. Add an explicit assertion that a non-owner chat never resolves to OPERATOR_USER_ID.
- operator_only decorator is defined but not actually applied to decision-queue / merge / spec-queue / memory-write functions as the spec requires; isolation currently relies only on the tenant command branch limiting commands. Acceptable for v0.1 but the spec's hard boundary is not enforced in code — note as deferred, not done.
- Default DB credential literal in tools/db/migrate_add_user_agents.py ('postgres://brain_index:changeme@...'); env-overridable but a hardcoded fallback cred in-repo is poor hygiene.
- tg_messages fallback in recent_context queries WHERE chat_id = user_id; for tenant ids like 'tg_<id>' this won't match and silently returns nothing — low impact (only on thread-table-missing exception path) but worth confirming.
- Migration/live verification not performed: schema migration not run against live Postgres and d034 user_channels shape unverified — a live mapped-tenant smoke test (tenant chats, James gets NO capture notification, tg_capture ignores tenant turns, thread.py recent shows only james) must pass before merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
