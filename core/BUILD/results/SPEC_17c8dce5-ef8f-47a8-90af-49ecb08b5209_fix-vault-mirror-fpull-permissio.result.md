# SPEC_17c8dce5-ef8f-47a8-90af-49ecb08b5209_fix-vault-mirror-fpull-permissio Result

- Status: done in working tree / awaiting merge review
- Branch: `build/SPEC_17c8dce5-ef8f-47a8-90af-49ecb08b5209_fix-vault-mirror-fpull-permissio`
- Files changed: `tools/decisions/mirror_pull.py`; `tools/decisions/test_mirror_pull.py`; `core/BUILD/specs/SPEC_17c8dce5-ef8f-47a8-90af-49ecb08b5209_fix-vault-mirror-fpull-permissio.md`; `core/BUILD/results/SPEC_17c8dce5-ef8f-47a8-90af-49ecb08b5209_fix-vault-mirror-fpull-permissio.result.md`; `core/BUILD/REGISTRY.json`; `docs/codex/HANDOFF.md`

## Summary

Hardened `tools/decisions/mirror_pull.py` so `fpull` no longer treats an existing but TCC-blocked macOS iCloud Obsidian path as the only vault target. Vault resolution now:

- honors explicit `FPAI_VAULT`,
- prefers the local `~/Documents/FPOS/Full Potential OS` vault when it exists,
- can still use an existing iCloud-only vault,
- falls back to the local Documents vault when an iCloud candidate raises `PermissionError` on mkdir/write.

The digest write now goes through a small fallback helper, and the follow-on state-doc mirror writes to the same vault that accepted the digest.

## Tests

- `python3 -B -m unittest tools.decisions.test_mirror_pull` (3 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/decisions/mirror_pull.py tools/decisions/test_mirror_pull.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks

- A live `fpull`/SSH brain digest pull was not run in this sandbox.
- If `FPAI_VAULT` is explicitly set to an inaccessible path, the script still fails rather than silently choosing another vault; this is intentional because explicit operator configuration should be trusted or fixed.

## Rollback

Revert `tools/decisions/mirror_pull.py`, remove `tools/decisions/test_mirror_pull.py`, remove this result/spec entry, and restore the registry row.

## Intent

- Intent solved: `fpull` vault mirroring no longer fails only because the iCloud Obsidian path exists but macOS denies unattended writes.
- Downstream intent unlocked: Ember can refresh the vault mirror from the safe local vault path without James manually working around TCC each run.
- Next unlocked move: after merge on the Mac, run the real `fpull` once and confirm `BRAIN DIGEST.md` plus mirrored state docs land in `~/Documents/FPOS/Full Potential OS`.
