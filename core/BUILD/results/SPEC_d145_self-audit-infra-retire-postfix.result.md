# SPEC d145 Result - Retire Postfix On 198

Status: done in working tree / awaiting review
Branch: `build/SPEC_d145_self-audit-infra-retire-postfix`
Date: 2026-07-03

## Summary

Added a reversible Postfix retirement helper for host `198.54.123.234`.
The activation script calls `tools.infra.retire_postfix_198` in execute mode.
The helper confirms Brevo outbound coverage from
`core/STATE/RESOURCE_INVENTORY.md`, only runs `systemctl disable --now postfix`
when the local host IP list includes `198.54.123.234`, and appends an ops-ledger
proof row with Brevo evidence, before/after service state, and rollback command.

If activation runs on a non-target host, it logs/skips and takes no service
action.

## Files Changed

- `tools/infra/retire_postfix_198.py`
- `tools/infra/test_retire_postfix_198.py`
- `core/BUILD/activate/SPEC_d145_self-audit-infra-retire-postfix.sh`
- `docs/infrastructure/postfix_198_retirement.md`
- `core/BUILD/specs/SPEC_d145_self-audit-infra-retire-postfix.md`
- `core/BUILD/results/SPEC_d145_self-audit-infra-retire-postfix.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.infra.test_retire_postfix_198` (3 OK)
- `bash -n core/BUILD/activate/SPEC_d145_self-audit-infra-retire-postfix.sh`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/infra/retire_postfix_198.py tools/infra/test_retire_postfix_198.py`
- `python3 -B -m tools.infra.retire_postfix_198 --repo-root . --ops-ledger /tmp/d145-ops-ledger.jsonl`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d145-registry.json`
- `git diff --check`

## Risks

This sandbox did not stop a live service because it is not host
`198.54.123.234`. The activation is guarded by local IP detection; if the
post-merge runner is not 198, the ledger will record `skipped` and the actual
retirement still needs the activation to run on 198.

Repo evidence says Brevo covers outbound, but some legacy/service code still
contains local SMTP/Postfix references. The d145 helper intentionally follows
the answered decision and verifies the canonical resource inventory, not every
historic application path.

## Rollback

On `198.54.123.234`:

```bash
systemctl enable --now postfix
systemctl is-active postfix
systemctl is-enabled postfix
```

Reverting this branch removes the helper, activation script, result, and
runbook.

## Intent Solved

d145 turns the self-audit finding into a reversible, proof-logged service
retirement path for Postfix on 198.

## Downstream Intent Unlocked

The allocation audit can classify direct SMTP on 198 as retired once the target
host activation logs `succeeded`, reducing unmanaged infra surface while
preserving a one-command rollback.
