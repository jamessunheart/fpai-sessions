# SPEC — Cora Commons public front door

**Approved by:** James Sunheart in the active Codex task on 2026-10-12
**Branch:** `feat/cora-commons-front-door`

## Intent

Give Cora Commons a clear public page at `/coracommons/` and make the FullPotential.com homepage route visitors toward three tangible expressions of the larger vision: Cora Commons, Dream Big and Zen Village.

## Files allowed

- `sites/fullpotential-com/index.html`
- `sites/fullpotential-com/coracommons/index.html`
- `tools/public_site/test_cora_commons_front_door.py`
- `core/BUILD/specs/SPEC_cora-commons-front-door.md`
- `core/BUILD/results/SPEC_cora-commons-front-door.result.md`

## Boundaries

- Preserve the production-only Dream Big navigation link.
- Link Zen Village to its current booking request path, not the expired September retreat offer.
- Do not claim CORA is funded, redeemable or earned merely by uploading work.
- Do not change payment systems, credentials, Guide behavior, assessment behavior, Game behavior or server services.
- Production deployment must create a timestamped backup and copy only the homepage and new Cora Commons directory.

## Definition of done

- `/coracommons/` clearly explains the promise, BRICKS, the contribution loop, CORA and trust boundaries.
- Homepage surfaces Cora Commons, Dream Big and Zen Village above the Capital Commons explanation.
- Relevant links and HTML structure pass automated checks.
- Live homepage and `/coracommons/` return HTTP 200 after deployment.
