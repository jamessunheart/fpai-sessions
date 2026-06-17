Status: done / independently reviewed / awaiting merge review

## Summary

d065 defines and encodes a repo-local public/private data boundary policy. The build adds a canonical policy file, a reusable classifier/router/sanitizer, focused regression tests, and wires the existing visual digest public story feed to the shared boundary instead of its local regex-only checks.

Mixed conversations now route as `split`: public-safe fragments may continue after sanitization, while personal, sensitive, legal, treasury, relationship, correction-log, credential, and default-private unmatched material stays in the private lane. Public publication fails closed if sanitized text still matches internal/private/sensitive policy.

## Files Changed

- `core/STATE/PUBLIC_PRIVATE_DATA_BOUNDARY.json`
- `tools/public_private_boundary/__init__.py`
- `tools/public_private_boundary/boundary.py`
- `tools/public_private_boundary/test_boundary.py`
- `docs/codex/PUBLIC_PRIVATE_DATA_BOUNDARY.md`
- `tools/visual/visual_digest.py`
- `core/BUILD/specs/SPEC_d065_public-private-data-boundary-pol.md`
- `core/BUILD/results/SPEC_d065_public-private-data-boundary-pol.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.public_private_boundary.test_boundary tools.visual.test_visual_digest`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/public_private_boundary/__init__.py tools/public_private_boundary/boundary.py tools/public_private_boundary/test_boundary.py tools/visual/visual_digest.py tools/visual/test_visual_digest.py`
- `python3 -m json.tool core/STATE/PUBLIC_PRIVATE_DATA_BOUNDARY.json`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -B -m tools.public_private_boundary.boundary --route --json ...`
- `git diff --check`

## Independent Review

Independent AI review initially returned `REQUEST_CHANGES` for two real blockers:

- unmatched text classified public despite `default_lane: private`;
- phone numbers were not covered by sensitive identifier policy.

Both findings were fixed with regressions. Blocker-only re-review returned `APPROVE` with no remaining functional/privacy blockers.

## Risks

The classifier is conservative and pattern-based. It may route ambiguous public-safe text to the private lane until explicit public signals are added. This is intentional for the boundary policy, but future public surfaces may need small allowlist additions for approved recurring phrases.

This build did not send public posts, deploy, touch secrets, move money, call external APIs, push, or merge.

## Rollback

Revert the d065 files listed above. The immediate runtime rollback for the only wired surface is to revert `tools/visual/visual_digest.py`, which restores its previous local public-summary filtering.

## Intent Solved

Public-lane and private-lane data categories are now encoded in repo state and enforced by a reusable helper instead of being implicit per-surface regexes.

## Downstream Intent Unlocked

Future public outputs can call the shared boundary module before publishing, allowing public story/feed tooling to extract shareable signal from mixed private conversations without leaking personal or sensitive context.
