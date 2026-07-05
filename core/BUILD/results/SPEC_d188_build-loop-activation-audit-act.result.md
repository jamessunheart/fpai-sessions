# SPEC_d188 Build-Loop Activation Audit Result

build_kind=library

## Summary
- Added `tools/build_loop/activation_audit.py`, a read-only merged-build classifier that outputs JSON or Markdown ledgers and can fail on unexplained inert rows.
- Added `tools/build_loop/activation_policy.py`, enforcing the future activate-or-declare-inert rule.
- Wired activation-audit evidence into `tools/build_loop/self_audit.py`, `tools/hot_memory/scanners/ops_scanner.py`, and owner-chat live status.
- Updated the generated server build-loop spec prompt and pre-review gate so future builds must ship `core/BUILD/activate/${SPECID}.sh` or declare `build_kind=library` / `build_kind=inert`.
- Added `core/BUILD/activation_declarations.json` for six legacy merged records that predate the policy and have no repo-local activation/reference evidence.

## Proof
- `python3 -B -m unittest tools.build_loop.test_activation_audit tools.build_loop.test_activation_policy tools.build_loop.test_activation_policy_contract tools.build_loop.test_self_audit tools.hot_memory.test_hot_memory SERVICES.sunheart-brain.curator.test_live_system_status` — 26 OK
- `python3 -B -m unittest tools.build_loop.test_liveness_probe tools.build_loop.test_auto_merge_governance tools.build_loop.test_parallel_build_loop tools.build_loop.test_build_state` — 19 OK
- `bash -n tools/build_loop/server_build_loop.sh`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/activation_audit.py tools/build_loop/activation_policy.py tools/build_loop/self_audit.py tools/hot_memory/scanners/ops_scanner.py SERVICES/sunheart-brain/curator/live_system_status.py tools/build_loop/test_activation_audit.py tools/build_loop/test_activation_policy.py tools/build_loop/test_activation_policy_contract.py`
- `python3 tools/build_loop/activation_audit.py --repo-root . --ops-ledger /tmp/fpai-missing-ops.jsonl --fail-on-unexplained-inert --output /tmp/d188-activation-audit.json`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d188_build-loop-activation-audit-act --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d188-registry.json`
- `python3 -m json.tool core/BUILD/activation_declarations.json >/tmp/d188-activation-declarations.json`
- `git diff --check`

## Ledger
See `core/BUILD/results/SPEC_d188_activation_audit_ledger.md`.

Current repo-local audit proof: 6 merged legacy records audited; 0 unexplained inert builds.

## Risks
- The sandbox did not read the live `/opt/fpai-build/ops_ledger.jsonl`, so live activation evidence may classify more rows as `auto-activated` after merge on server 162.
- The legacy declaration file is intentionally an explanation, not activation. Those rows remain `INERT`; they are just no longer silent.
- Reference detection is conservative and section-scoped to result `Files Changed` data; missing or poorly formatted result artifacts may need explicit `build_kind` declarations.

## Rollback
Revert this branch. The audit is read-only; the policy gate can be disabled only by reverting the `server_build_loop.sh` hook and generated-spec text.

## Intent Solved
Merged no longer silently means used: the loop can measure auto-activated, library/reference-backed, and inert builds.

## Downstream Intent Unlocked
Future capability builds must activate themselves or explicitly declare why they are library/inert before independent review and merge.
