# SPEC_d062_ai-pairing-account-security-bind Result

- Status: done / independently reviewed / awaiting merge review
- Branch: `build/SPEC_d062_ai-pairing-account-security-bind`
- Completed: 2026-06-17T00:35:48Z

## Summary

Added verified AI/user pairing security for the Sunheart Brain Telegram surface.
The build adds durable pairing tables, a reusable guard module, optional runtime
enforcement, account-takeover drift detection, docs, and an initial report-only
signal artifact.

## Files Changed

- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/index/schema.sql`
- `tools/identity_pairing/__init__.py`
- `tools/identity_pairing/guard.py`
- `tools/identity_pairing/test_guard.py`
- `docs/codex/AI_PAIRING_ACCOUNT_SECURITY.md`
- `core/BUILD/signals/ai_pairing_security.json`
- `core/BUILD/signals/ai_pairing_security.md`
- `core/BUILD/specs/SPEC_d062_ai-pairing-account-security-bind.md`
- `core/BUILD/results/SPEC_d062_ai-pairing-account-security-bind.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.identity_pairing.test_guard` (7 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/identity_pairing/guard.py tools/identity_pairing/test_guard.py SERVICES/sunheart-brain/curator/tgbot.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool core/BUILD/signals/ai_pairing_security.json`

## Independent Review

Independent AI review found one P1 blocker: owner/team messages could fail open
if `AI_PAIRING_ENFORCE=1` and the guard errored. Fixed by making message
handling fail closed in enforcement mode. Blocker-only re-review reported no
remaining blockers.

## Risks

- Live pairing rows were not seeded in this sandbox.
- `AI_PAIRING_ENFORCE=1` should not be enabled on the live bot until Ember seeds
  at least the verified James pairing and runs one live proof.
- This is not hardware attestation, device MFA, or provider-side account
  recovery; it is an AI-surface binding and drift guard.

## Rollback

Unset `AI_PAIRING_ENFORCE` for immediate compatibility-mode rollback. To remove
the build, revert the files listed above. If the schema was applied live, keep
or export `ai_pairing_security_events` before dropping the two d062 tables.

## Intent Solved

AI-facing user pairings no longer have to rely only on static chat-id allowlists;
they can be bound to verified identity rows with fail-closed enforcement and
auditable drift events.

## Downstream Intent Unlocked

Ember can seed verified live pairings, enable enforcement for the Telegram brain
bot, and route follow-up hardening for additional AI surfaces without letting an
account-takeover drift silently inherit AI privileges.

