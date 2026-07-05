# SPEC_d186 Opportunity Intelligence Engine Result

## Summary
- Added `tools/allocation/opportunity_engine.py`: JSON Opportunity Portfolio, five seeded opportunities, 8-question fields, numeric axes, Opportunity Score, Allocation Score, closest-to-cash ranking, and cheap gap scan metadata.
- Scores stay blank when required axes are missing; narrative unknowns remain blank instead of inferred.
- Wired Chief of Staff `/opportunities` and digest metrics.
- Wired Telegram `/opportunities` to return the ranked portfolio immediately and trigger the existing opportunities scan asynchronously.
- Wired curator opportunities/digest jobs to update and surface the portfolio.
- Wired council debate prompt to read top Allocation Score opportunities before proposing a build; existing Council + Constitution Check gates still control build arming.

## Seed Portfolio
- Resource Optimization Audit
- AI Voice Receptionist
- Medical Documentation Agent
- Finance Allocation Engine
- Opportunity Intelligence Engine

## Proof
- `python3 -B -m unittest tools.allocation.test_opportunity_engine tools.allocation.test_capability_ledger tools.council.test_debate SERVICES.sunheart-brain.curator.test_tgbot_act_bridge`
- `PYTHONPATH=SERVICES/chief-of-staff:. python3 -B -m unittest app.test_capability`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/allocation/opportunity_engine.py tools/allocation/test_opportunity_engine.py SERVICES/chief-of-staff/app/opportunities.py SERVICES/chief-of-staff/app/digest.py SERVICES/chief-of-staff/app/main.py SERVICES/chief-of-staff/app/test_capability.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_act_bridge.py SERVICES/sunheart-brain/curator/jobs/opportunities.py SERVICES/sunheart-brain/curator/jobs/digest.py tools/council/debate.py tools/council/test_debate.py`
- `FPAI_OPPORTUNITY_WEB=0 python3 tools/allocation/opportunity_engine.py --ledger /tmp/d186-opportunities.json`
- `FPAI_OPPORTUNITY_WEB=0 python3 tools/allocation/opportunity_engine.py --ledger /tmp/d186-opportunities.json --scan --scan-ledger /tmp/d186-scans.jsonl --json`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d186-registry-final-check.json`
- `git diff --check`

## Risks
- Live web scan, Chief of Staff startup, Telegram bot startup, and live DB/timer proof were not run in this sandbox.
- v1 seeded numeric axes are explicit first-pass ranking inputs, not verified market facts. Unknown narrative fields remain blank.
- The external web scanner is best-effort and free-signal only; failures skip silently rather than blocking the daily scan.

## Rollback
Revert this branch. Runtime mitigation without code rollback is to point `FPAI_OPPORTUNITY_LEDGER` at an empty JSON portfolio or set `FPAI_OPPORTUNITY_WEB=0` to disable web fetches.
