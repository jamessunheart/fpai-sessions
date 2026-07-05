# SPEC_d194_spec-d194-the-spot-topple-orches Result

## Status
Done in working tree / awaiting review + merge + activation.

## Files Changed
- `tools/build_loop/spot_topple_orchestrator.py`
- `tools/build_loop/test_spot_topple_orchestrator.py`
- `tools/allocation/opportunity_engine.py`
- `tools/allocation/test_opportunity_engine.py`
- `core/BUILD/cron/fpai-spot-topple.service`
- `core/BUILD/cron/fpai-spot-topple.timer`
- `core/BUILD/cron/fpai-spot-topple-run.sh`
- `core/BUILD/activate/SPEC_d194_spec-d194-the-spot-topple-orches.sh`
- `core/BUILD/specs/SPEC_d194_spec-d194-the-spot-topple-orches.md`
- `core/BUILD/results/SPEC_d194_spec-d194-the-spot-topple-orches.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Built the local Spot -> Topple -> Proof -> Learning orchestrator. It reads HOT_STATE/treasury/funnel/capability signals, runs the d186 opportunity gap scan without web calls, ranks the next domino, gates auto-topple through reversibility/cost/reserved-word/constitution checks, optionally queues one answered `needs_build=true` decision, writes an auditable JSONL cycle ledger, writes a one-line digest, and suppresses duplicate queues for 24 hours.

Dogfood seed added to the Opportunity Engine: `Assessment Funnel Delivery Proof`, which re-spots the d193 funnel-delivery domino as the top next domino and treats real end-to-end proof as required before counting the domino toppled.

Activation ships a systemd timer (`fpai-spot-topple.timer`) that runs every 2 hours through `core/BUILD/cron/fpai-spot-topple-run.sh`. Kill switch: `touch /opt/fpai-build/.spot_topple_disabled`.

## Tests
- `python3 -B -m unittest tools.build_loop.test_spot_topple_orchestrator tools.allocation.test_opportunity_engine`
- `python3 -B -m unittest tools.build_loop.test_spot_topple_orchestrator tools.allocation.test_opportunity_engine tools.allocation.test_capability_ledger tools.build_loop.test_activation_audit tools.governance.test_constitution_check`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/spot_topple_orchestrator.py tools/build_loop/test_spot_topple_orchestrator.py tools/allocation/opportunity_engine.py tools/allocation/test_opportunity_engine.py`
- `tmp=$(mktemp -d); python3 -B tools/build_loop/spot_topple_orchestrator.py --repo-root . --opportunity-ledger "$tmp/opportunities.json" --opportunity-scan-ledger "$tmp/scans.jsonl" --capability-ledger "$tmp/capability.jsonl" --ops-ledger "$tmp/ops.jsonl" --cycle-ledger "$tmp/cycles.jsonl" --digest "$tmp/digest.txt" --kill-switch "$tmp/disabled" --hot-state core/STATE/HOT_STATE.md --treasury-signal core/STATE/TREASURY_TODAY.md --funnel-signal core/BUILD/signals/funnel_metrics.json --dry-run --json`
- `bash -n core/BUILD/activate/SPEC_d194_spec-d194-the-spot-topple-orches.sh core/BUILD/cron/fpai-spot-topple-run.sh`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d194_spec-d194-the-spot-topple-orches --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d194-registry-building.json`
- `git diff --check`

## Proof
CLI smoke spotted `Assessment Funnel Delivery Proof`, returned `auto_topple_ready=true`, estimated daily cost `$0`, passed the Constitution check, wrote the digest shape, and withheld queueing under `--dry-run`. Unit proof covers kill switch behavior, duplicate suppression, injected queue payload, reserved-word rejection, and d193 funnel-domino ranking.

## Risks
Live timer activation, live DB queue insert, live d193 activation evidence, and the actual test-lead submission were not run in this sandbox. The timer will queue if `BRAIN_INDEX_DB_URL` is present and the gate passes; duplicate suppression prevents the same top domino from being queued again within 24 hours.

## Rollback
Revert this branch. If activated, run `systemctl disable --now fpai-spot-topple.timer`, remove `/etc/systemd/system/fpai-spot-topple.{service,timer}`, run `systemctl daemon-reload`, and optionally remove `/opt/fpai-build/spot_topple_ledger.jsonl` plus `/opt/fpai-build/spot_topple_digest.txt` after review.

## Intent solved
SPOT no longer depends on James/Ember prompting; the substrate has a scheduled local scanner that can identify and safely queue reversible next dominoes.

## Downstream intent unlocked
After merge/activation, the build loop can run Spot -> Topple -> real-execution proof -> capability learning on cadence, with James seeing only reserved gates or a one-line proof digest.
