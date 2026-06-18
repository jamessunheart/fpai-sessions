# Codex build result - SPEC_d116_retroactive-liveness-audit-scan
_ran: 2026-06-18T21:45:15Z · branch: build/SPEC_d116_retroactive-liveness-audit-scan_

## Summary
Built `tools/liveness/retroactive_audit.py`, a bounded one-time audit helper for merged d001-d092 decisions. It discovers merged decisions from result/activation artifacts and ops-ledger merge evidence, infers expected artifacts from activation scripts, result files, specs, repo paths, systemd units, DB table references, and endpoints, writes `liveness_audit.md` as a three-column table, appends an ops-ledger row, optionally notifies Telegram, and seeds `dNNN-activate` follow-up decisions for concrete `dead` rows.

The script is conservative: unavailable systemd bus, missing DB driver/connection, and disabled external endpoint probing become `unknown`, not `dead`.

## Sandbox audit output
- `liveness_audit.md` produced.
- Counts in this restricted worktree: `live=16`, `dead=6`, `unknown=21`.
- The sandbox run used `--no-seed --no-notify --ops-ledger /tmp/d116_liveness_ops.jsonl` because live DB writes and Telegram sends are outside this environment.

## Files changed
- `tools/liveness/__init__.py`
- `tools/liveness/retroactive_audit.py`
- `tools/liveness/test_retroactive_audit.py`
- `liveness_audit.md`
- `core/BUILD/specs/SPEC_d116_retroactive-liveness-audit-scan.md`
- `core/BUILD/results/SPEC_d116_retroactive-liveness-audit-scan.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests
- `python3 -B -m unittest tools.liveness.test_retroactive_audit` - 8 tests OK.
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/liveness/retroactive_audit.py tools/liveness/test_retroactive_audit.py` - OK.
- `python3 -m json.tool core/BUILD/REGISTRY.json` - OK.
- `python3 -B -m tools.liveness.retroactive_audit --output liveness_audit.md --ops-ledger /tmp/d116_liveness_ops.jsonl --no-seed --no-notify` - produced report and ledger row.

## Risks
- The real one-time audit must run on server 162 without `--no-seed --no-notify` to update `brain_index.decisions` and Telegram. This sandbox cannot prove live DB writes, live table row counts, active systemd units, or Telegram delivery.
- Artifact inference is heuristic. It avoids declaring unavailable evidence dead, but dead follow-ups should still be reviewed as activation-scoped repairs before merge.
- External endpoints are not probed unless `--allow-external-endpoints` is set; by default they remain `unknown`.

## Rollback
Revert the listed files and remove `liveness_audit.md`. If the live script later seeds follow-up decisions that should be undone, close or remove the affected `dNNN-activate` rows from `brain_index.decisions`.

## Intent solved
Merged d001-d092 builds now have a deterministic retroactive liveness audit path instead of relying on stale merge/result artifacts.

## Downstream intent unlocked
Server 162 can run the audit once and queue focused activation specs only for concrete dead merged builds, closing the pre-d115 merged-but-not-live gap.
