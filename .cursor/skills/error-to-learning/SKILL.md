---
name: error-to-learning
description: >-
  5-step protocol to follow whenever you fix any error: fix, root-cause, add
  regression test, log to /opt/fpai/learnings.json, update process docs if
  systemic. Use any time an error, exception, failing test, or unexpected
  behavior is being resolved — regardless of domain.
---

# Error → Learning Protocol

**Recommended model:** Claude 4.7 Opus (root-cause analysis benefits from depth and self-correction; the cost is justified by avoiding the same bug twice).

Every fix must leave the system a little smarter. Five steps, in order.

## 1. Fix it

Apply the immediate fix. Confirm it works (run the failing scenario, not just the related test).

## 2. Root cause

Do not stop at "what was wrong." Ask: **why wasn't this caught?**
- Missing test?
- Missing lint rule?
- Silent failure mode?
- Hidden coupling between two systems?
- Version drift between environments?

Write the root-cause sentence in plain language.

## 3. Add a regression test

Location: `/opt/fpai/tests/` (or the closest existing test dir for that component).

The test should fail on the pre-fix code and pass on the fixed code. Name it after the error, not the fix ("test_whaletrack_alert_silent_on_missing_telegram_token" beats "test_sends_alert").

## 4. Log to central memory

Append a JSON record to `/opt/fpai/learnings.json`:

```json
{
  "date": "YYYY-MM-DD",
  "error": "short description of what broke",
  "root_cause": "why it broke",
  "why_missed": "why our existing checks didn't catch it",
  "fix": "what you changed",
  "test_added": "path or id of the regression test",
  "scope": "service or subsystem affected"
}
```

This file syncs to the agent memory layer on startup. Future sessions (human and agent) benefit from it.

## 5. Update process docs — if systemic

If this is a class of problem (not a one-off), update the relevant memory doc under `/opt/fpai/docs/coordination/MEMORY/*.md`. Examples:

- Deployment surprise → `WEB_DEPLOYMENT_PROTOCOL.md` or `VERSION_CONTROL_PROTOCOL.md`
- Coordination failure → `MULTI_SESSION_COORDINATION.md`
- Recurring class of bug → add a rule under `.cursor/rules/` so the agent catches it next time.

## Done looks like

A one-paragraph summary to the user:
1. What broke, in plain terms.
2. The fix.
3. The regression test you added (path).
4. Whether you updated any process docs — and which.

Related: `@docs/coordination/MEMORY/ERROR_LEARNING_PROTOCOL.md`.
