# AI Review — build/SPEC_d099_postiz-social-scheduler-mcp-wire

**Verdict:** APPROVE · **Risk:** low

**Summary:** Repo-side Postiz MCP wiring (dry-run payload helper, non-secret MCP fragment, multi-gated activation script, tests) — no live deploy, no secrets, no money/prod writes; safe and within spec scope.

## Findings
- No secrets committed — MCP fragment and config use ${POSTIZ_API_KEY} placeholder only (verified by test_config_fragment_has_no_secret_value).
- Activation script that touches server 162 (git clone + docker compose up) is triple-gated (POSTIZ_ACTIVATE=1, POSTIZ_START=1, POSTIZ_ENV_READY=1) and dry-run by default; it is only committed code, not executed by this build. Acceptable but the live run remains a manual prod action to watch.
- Payload validator rejects unsafe HTML (<script/javascript:) and enforces paragraph HTML + UTC-Z timestamps; html.escape applied to content. Reasonable input hygiene.
- Scope matches spec: activation artifact, MCP fragment, dry-run schedulePostTool helper, and focused tests (6 passing). No scope creep into live send/publish, account creation, or push/merge.
- Minor: MCP URL embeds the API key in the URL path — this mirrors Postiz's own MCP design, not a flaw introduced here, but operators should treat the installed fragment (chmod 0600) as a secret.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
