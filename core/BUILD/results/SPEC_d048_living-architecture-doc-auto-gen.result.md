# SPEC_d048_living-architecture-doc-auto-gen Result

- Status: done
- Branch: `build/SPEC_d048_living-architecture-doc-auto-gen`
- Tests: passed
- Cost: ~$0 marginal, Codex flat-rate

## Summary

Built the living architecture SSOT:

- Added `docs/ARCHITECTURE.md` as the generated, shareable architecture document.
- Added `tools/docs/generate_architecture.py` with repo-registry status inference, live `brain_index.decisions` queue reads when DB env is available, `systemctl list-units` service snapshots, ops-ledger logging, and `ARCHITECTURE_DISABLE=1`.
- Added focused generator tests.
- Wired best-effort architecture regeneration after successful merges in `tools/merge/process_merge_requests.sh` and `tools/build_loop/build_orchestrator.sh`.
- Registered d048 in `core/BUILD/REGISTRY.json`.

## Verification

- `python3 -B -m unittest tools.docs.test_generate_architecture`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/docs/generate_architecture.py tools/docs/test_generate_architecture.py`
- `bash -n tools/merge/process_merge_requests.sh tools/build_loop/build_orchestrator.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`

## Notes

The sandbox does not have live `brain_index` credentials or server-162 `systemctl` access, so the generated document currently shows honest unavailable placeholders for those live sections. On server 162, the same generator will populate those sections from `BRAIN_INDEX_DB_URL` and local systemd state.
