# SPEC_d091_resource-inventory-system-knows Result

- Status: done in working tree / independent AI review blocked in sandbox / awaiting merge review
- Branch: `build/SPEC_d091_resource-inventory-system-knows`
- Files changed: `tools/inventory/__init__.py`; `tools/inventory/scan_resources.py`; `tools/inventory/test_scan_resources.py`; `core/STATE/AVAILABLE_RESOURCES.md`; `core/BUILD/cron/fpai-resource-inventory.service`; `core/BUILD/cron/fpai-resource-inventory.timer`; `tools/council/debate.py`; `tools/council/test_debate.py`; `core/BUILD/specs/SPEC_d091_resource-inventory-system-knows.md`; `core/BUILD/results/SPEC_d091_resource-inventory-system-knows.result.md`; `core/BUILD/REGISTRY.json`; `docs/codex/HANDOFF.md`

## Summary

Added `tools/inventory/scan_resources.py`, a side-effect-free local inventory scanner that writes `core/STATE/AVAILABLE_RESOURCES.md`. It records CLI availability for the requested tool list, installed pip distributions via `pkg_resources`, non-secret configured API/env variable names with values omitted, and script-shaped files under `/opt/fpai`.

Added reviewed weekly systemd artifacts, `fpai-resource-inventory.service` and `fpai-resource-inventory.timer`, for later live installation by Ember. `tools/council/debate.py` now loads `AVAILABLE_RESOURCES.md` into the debate prompt alongside `COUNCIL_FOCUS.md`, and tests prove the next debate context can reference an inventory tool such as `git`.

## Tests

- `python3 -m tools.inventory.scan_resources`
- `python3 -B -m unittest tools.inventory.test_scan_resources tools.council.test_debate` (8 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/inventory/__init__.py tools/inventory/scan_resources.py tools/inventory/test_scan_resources.py tools/council/debate.py tools/council/test_debate.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d091-registry.json`

## Review

Independent AI review was attempted with `claude -p --effort high` against `/tmp/d091-full.patch`, including untracked files. It produced no output after roughly 90 seconds and was terminated; no independent review verdict is available in this sandbox.

## Risks

No live timer install, production deploy, external API call, secret read, push, or merge was performed. The inventory file records names and paths only; environment variable values are never written, and secret-shaped variable names are omitted.

## Rollback

Revert the d091 files listed above. If the timer is installed later, disable/remove `fpai-resource-inventory.timer` and `fpai-resource-inventory.service`.

## Intent

- Intent solved: council and forge can now see what tools, packages, configured APIs, and local scripts already exist on the server before proposing new builds.
- Downstream intent unlocked: future council proposals can route resource-aware specs that reuse installed CLIs/libraries instead of proposing blind duplicate integrations.
- Next move: rerun independent AI review from a live/writable host if required; after merge, Ember can install/enable the weekly timer artifact and run one council cycle to confirm the surfaced proposal references at least one inventory resource.
