# SPEC_d185 Capability-Created Ledger Result

## Summary
- Added `tools/allocation/capability_ledger.py` for honest-zero capability scoring across `time_saved`, `knowledge_gained`, `cash_flow`, `trust`, and `automation`, with extensible extra axes.
- Added realized vs expected capability totals so the 7-Q estimator can compare expected gain to realized gain.
- Added reusable-intelligence enforcement for positive scored rows.
- Added Chief of Staff `/capability` view, Telegram `/capability` command, and a daily digest headline line.
- Added one d185 proof fixture row: +4 total capability, with no time or cash gain claimed.

## Proof
- `python3 -B -m unittest tools.allocation.test_capability_ledger`
- `PYTHONPATH=SERVICES/chief-of-staff:. python3 -B -m unittest app.test_capability`
- `python3 -B -m unittest SERVICES.sunheart-brain.curator.test_tgbot_act_bridge`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/allocation/capability_ledger.py tools/allocation/test_capability_ledger.py SERVICES/chief-of-staff/app/capability.py SERVICES/chief-of-staff/app/digest.py SERVICES/chief-of-staff/app/main.py SERVICES/chief-of-staff/app/test_capability.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_act_bridge.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d185-registry.json`
- `git diff --check`
- `python3 tools/allocation/capability_ledger.py --ledger core/BUILD/results/SPEC_d185_capability_created.fixture.jsonl`

## Capability Row
Fixture: `core/BUILD/results/SPEC_d185_capability_created.fixture.jsonl`

`capability created today: +4 (time+0 knowledge+1 cash+0 trust+1 auto+2).`

## Risks
- The live Chief of Staff dependency environment was not started in this sandbox.
- `/capability` reads `FPAI_CAPABILITY_LEDGER` or `~/.config/fpai/allocation/ledger.jsonl`; until live rows are appended there, live output is honestly zero.

## Rollback
Revert this branch. Runtime mitigation without code rollback is to leave `FPAI_CAPABILITY_LEDGER` unset or point it at an empty ledger.
