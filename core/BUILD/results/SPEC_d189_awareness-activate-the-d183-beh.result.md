# SPEC_d189_awareness-activate-the-d183-beh Result

build_kind=activated

## Summary

Activated the d183 behavioral awareness probe as the live signal path instead of leaving it as merged-inert code. `awareness_reliability.json` now declares `primary_metric=behavioral_bot_answer` and `secondary_signal=context_render_continuity`, so downstream readers do not conflate bot-answer correctness with the old title-in-render continuity check. Failed behavioral grading now reports `behavioral bot answer missed expected latest-insight keywords`, which is explicitly a behavioral grading reason and not the retired string-match proxy.

The systemd service now runs through `core/BUILD/cron/fpai-awareness-reliability-run.sh`, which uses `/opt/sh-brain-src/.venv/bin/python` when available. This closes the observed `No module named 'psycopg'` failure mode from running the timer under plain system Python.

Added `core/BUILD/activate/SPEC_d189_awareness-activate-the-d183-beh.sh`. It installs the reviewed service/timer, enables the timer, runs one live probe, and validates that the resulting report has a real question, a real bot answer, a boolean `behavioral_pass`, and a separate boolean `context_render_continuity`. It rejects reports that still look like the retired context-render title proxy or the ambiguous d183 reason text.

## Files Changed

- `tools/awareness/verify_awareness.py`
- `tools/awareness/reliability_probe.py`
- `tools/awareness/test_reliability_probe.py`
- `core/BUILD/cron/fpai-awareness-reliability.service`
- `core/BUILD/cron/fpai-awareness-reliability-run.sh`
- `core/BUILD/activate/SPEC_d189_awareness-activate-the-d183-beh.sh`
- `core/BUILD/specs/SPEC_d189_awareness-activate-the-d183-beh.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d189_awareness-activate-the-d183-beh.result.md`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.awareness.test_reliability_probe tools.continuity.test_write_session_insights` — 11 OK
- `python3 -B -m unittest tools.build_loop.test_activation_policy tools.build_loop.test_activation_policy_contract` — 6 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/awareness/verify_awareness.py tools/awareness/reliability_probe.py tools/awareness/test_reliability_probe.py`
- `bash -n core/BUILD/cron/fpai-awareness-reliability-run.sh core/BUILD/activate/SPEC_d189_awareness-activate-the-d183-beh.sh`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d189_awareness-activate-the-d183-beh --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d189-registry.json`
- `git diff --check`

## Live Verification

Sandbox verification with system Python proved the old execution path fails before DB lookup with `No module named 'psycopg'`. Running through `/opt/sh-brain-src/.venv/bin/python` proved the venv has `psycopg`, but this sandbox could not connect to the live DB (`connection is bad`), so it could not ask the live bot here. The activation script is intentionally strict and will fail on server 162 if DB access, bot answering, or behavioral report shape is not live.

## Risks

- Full live behavioral answer proof awaits post-merge activation on server 162.
- Keyword grading is still deterministic; a valid answer that avoids expected terms can fail, but the report exposes answer and matched keywords for audit.
- Activation writes one live probe result and enables the existing timer; rollback is straightforward.

## Rollback

Revert this branch. If already activated, restore the previous `fpai-awareness-reliability.service` ExecStart or disable `fpai-awareness-reliability.timer`, then revert the repo changes. The probe writes only JSON/Markdown signal files and ops-ledger rows.

## Intent Solved

d183 is no longer merely merged; the live timer path is explicitly installed, venv-backed, and smoke-gated around behavioral bot-answer grading.

## Downstream Intent Unlocked

Awareness reliability can now function as a behavioral signal for the build loop instead of a title-string/context-render proxy, making future self-audit and routing decisions less cosmetic.
