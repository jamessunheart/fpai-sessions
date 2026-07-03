# d146 - self-audit infra cruft services

## Status

Built in working tree for review. Do not push or merge from this session.

## What changed

- Added `tools/infra/stop_cruft_services_198.py`, a target-host guarded helper for `198.54.123.234`.
- Added `core/BUILD/activate/SPEC_d146_self-audit-infra-cruft-services.sh` for post-merge activation.
- Added focused tests in `tools/infra/test_stop_cruft_services_198.py`.
- Registered the build in `core/BUILD/REGISTRY.json`.

## Behavior

The helper reads `core/STATE/FLEET_SNAPSHOT.md` and refuses to act unless the d146 cruft evidence names `cocoon` and `whaletrack-magnet`.

Live service control is gated three ways:

1. local IP list must include `198.54.123.234`;
2. activation must run with `--execute`;
3. `FPAI_D146_CRUFT_STOP=1` must be set.

When all three pass, it runs:

```bash
systemctl disable --now fpai-cocoon.service whaletrack-magnet.service
```

It records service active/enabled states and `/proc/meminfo` before/after, including `ram_reclaimed_kib`, to the ops ledger.

## Rollback

On `198.54.123.234`:

```bash
systemctl enable --now fpai-cocoon.service whaletrack-magnet.service
```

If the activation runs with the flag unset, it records `event=flag_disabled` and does not stop either service.

## Tests

- `python3 -B -m unittest tools.infra.test_stop_cruft_services_198`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/infra/stop_cruft_services_198.py tools/infra/test_stop_cruft_services_198.py`
- `bash -n core/BUILD/activate/SPEC_d146_self-audit-infra-cruft-services.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d146-registry.json`
- `python3 -B -m tools.infra.stop_cruft_services_198 --repo-root . --ops-ledger /tmp/d146-ops-ledger.jsonl --settle-seconds 0`
- `git diff --check`
