# SPEC_d089_payment-triggered-agent-spawn-c Result

- Status: done in working tree / commit blocked by read-only shared Git metadata / independent AI review blocked in sandbox / awaiting merge review
- Branch: `build/SPEC_d089_payment-triggered-agent-spawn-c`
- Files changed: `SERVICES/zend-payments/app/main.py`; `SERVICES/zend-payments/app/payment_activation.py`; `SERVICES/zend-payments/app/test_payment_activation.py`; `SERVICES/sunheart-brain/curator/users.py`; `SERVICES/sunheart-brain/curator/test_users.py`; `core/BUILD/specs/SPEC_d089_payment-triggered-agent-spawn-c.md`; `core/BUILD/REGISTRY.json`; `core/BUILD/results/SPEC_d089_payment-triggered-agent-spawn-c.result.md`; `docs/codex/HANDOFF.md`

## Summary

Wired `checkout.session.completed` in `zend-payments` to a paid-user activation path before the payment intent is marked settled. The activation extracts `user_id` from Stripe session metadata (`user_id`, `fpai_user_id`, `brain_user_id`) or `client_reference_id`, marks `brain_index.users.paid = TRUE`, calls `curator.users.init_namespace(user_id)`, then sends one Telegram message to the user's chat id with exactly `Your agent is ready.` The webhook now fails closed before settlement if activation or the first message is incomplete, preserving Stripe retry behavior instead of silently settling without an agent spawn.

Added `curator.users` as the d042-compatible namespace helper. It uses the existing `BRAIN_INDEX_DB_URL` connection helper when available, adapts to existing `users` and `user_agents` columns, reactivates archived namespace rows when supported, and does not add migrations or new infrastructure.

## Tests

- `python3 -B -m unittest app.test_payment_activation` from `SERVICES/zend-payments` (3 tests OK)
- `python3 -B -m unittest curator.test_users` from `SERVICES/sunheart-brain` (1 test OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/zend-payments/app/payment_activation.py SERVICES/zend-payments/app/main.py SERVICES/zend-payments/app/test_payment_activation.py SERVICES/sunheart-brain/curator/users.py SERVICES/sunheart-brain/curator/test_users.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d089-registry.json`
- `git diff --check`
- explicit `git diff --check --no-index` over new untracked files

## Independent Review

Attempted `claude -p --effort high` against `/tmp/d089-full.patch`, including untracked files. The command produced no output after roughly two minutes and could not be interrupted through the closed stdin session; no independent review verdict is available in this sandbox. Rerun independent review from the live/writable host before merge if required.

## Commit

Local commit was attempted with `git add ... && git commit -m "feat(payments): spawn agent on checkout completion"` and failed because Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d089_payment-triggered-agent-spawn-c/index.lock`: read-only file system. Changes remain in the working tree.

## Risks

No live Stripe webhook, brain-index write, Telegram send, deploy, push, merge, or secret read occurred in this sandbox. Live activation depends on Stripe checkout sessions carrying a user id and either a Telegram chat id in metadata or a chat id column on `brain_index.users`. The live `user_agents` schema is inferred dynamically; if required columns differ from the supported `user_id`/`namespace`/`status`/`archived`/timestamps shape, the webhook will fail closed and Stripe should retry after the schema/helper is corrected.

## Rollback

Revert the files listed above. Runtime rollback for any completed activation is the spec rollback: set `brain_index.users.paid = FALSE` for the affected user and archive that user's namespace row in `brain_index.user_agents`.

## Intent

- Intent solved: a completed Stripe checkout now triggers the paid flag, per-user namespace initialization, and the first Telegram readiness message.
- Downstream intent unlocked: the product can run a real cell-division proof where one payment creates one namespaced user agent with an immediate first contact.
- Next unlocked move: run a live Stripe test checkout with metadata `{user_id, telegram_chat_id}` on the live host, verify `users.paid`, verify the `user_agents` namespace row, and confirm the Telegram message.
