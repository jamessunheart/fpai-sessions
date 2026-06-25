# SPEC_d090_payment-triggered-agent-spawn Result

- Status: done in working tree / commit blocked by read-only Git metadata / independent AI review blocked in sandbox / awaiting merge review
- Branch: `build/SPEC_d090_payment-triggered-agent-spawn`
- Files changed:
  - `tools/payments/__init__.py`
  - `tools/payments/agent_spawn.py`
  - `tools/payments/schema.sql`
  - `tools/payments/test_agent_spawn.py`
  - `core/BUILD/specs/SPEC_d090_payment-triggered-agent-spawn.md`
  - `core/BUILD/results/SPEC_d090_payment-triggered-agent-spawn.result.md`
  - `core/BUILD/REGISTRY.json`
  - `docs/codex/HANDOFF.md`

## Summary

Added a guarded payment-event-to-agent-namespace spawn scaffold. `tools/payments/agent_spawn.py` accepts already-delivered billing webhook payloads, validates an enable flag, verifies an HMAC webhook signature for HTTP handling, recognizes paid Stripe-shaped events, rejects unpaid/unsupported/missing-identity events, and idempotently creates one `brain_index.user_agents` namespace plus one `brain_index.payment_agent_spawns` record per payment event. `tools/payments/schema.sql` documents the live DB tables for later activation.

The build does not create Stripe products, call Stripe, move money, deploy a webhook, install services, read secrets, push, or merge.

## Tests

- `python3 -B -m unittest tools.payments.test_agent_spawn` (5 tests OK)
- `python3 -B -m unittest tools.payments.test_agent_spawn tools.probe.test_inbound` (9 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/payments/__init__.py tools/payments/agent_spawn.py tools/payments/test_agent_spawn.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d090-registry.json`
- `git diff --check`

## Independent Review

Generated `/tmp/d090-full.patch` including untracked files and attempted:

`/root/.local/bin/claude -p --effort high "$(cat /tmp/d090-review-prompt.txt)"`

The review failed with `API Error: Unable to connect to API (ConnectionRefused)`. No independent AI approval is available in this sandbox; rerun review from a live/writable host before merge if required.

## Commit

Attempted `git add ... && git commit -m "Add payment-triggered agent namespace spawn"`. Git failed with `fatal: Unable to create '/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d090_payment-triggered-agent-spawn/index.lock': Read-only file system`. The branch changes remain in the working tree and need staging/commit from a writable Git context.

## Risks

- Live activation still needs the billing provider/webhook layer to pass the raw event body and `X-FPAI-Payment-Signature` generated with `PAYMENT_AGENT_SPAWN_SECRET`.
- SQL was not applied to a live DB in this sandbox.
- Namespace isolation is represented by deterministic IDs and DB uniqueness; broader per-user runtime isolation/grants should be validated in the next live adapter spec before multi-user autonomy depends on it.

## Rollback

Revert the d090 files listed above and remove the registry/handoff/result entries. If later applied live, drop or archive `brain_index.payment_agent_spawns` and any `brain_index.user_agents` rows whose `source_event_id` came from the reverted payment events.

## Intent

- Intent solved: a paid billing event can now deterministically and idempotently become an agent namespace record behind explicit live gates.
- Downstream intent unlocked: the live billing webhook can be connected in a tiny activation spec to prove paid user cell division without James manually creating agent namespaces.
- Next unlocked move: run independent review from a live host, apply the SQL on the target DB, mount `/payments/agent-spawn` behind the existing billing webhook, and fire one signed fixture event before any real payment event is allowed through.
