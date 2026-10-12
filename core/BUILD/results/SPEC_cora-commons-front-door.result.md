# Result — Cora Commons public front door

**Date:** 2026-10-12
**Branch:** `feat/cora-commons-front-door`
**Status:** deployed and HTTPS-verified

## Intent solved

Cora Commons now has a clear public explanation at `https://fullpotential.com/coracommons/`, and the FullPotential.com homepage routes people toward three tangible expressions of the larger vision: Cora Commons, Dream Big and Zen Village.

## Downstream intent unlocked

The public invitation can now be tested with real prospective contributors. Homepage visitors can also reach the existing Dream Big page and the current Zen Village booking request without navigating through abstract system concepts first.

## Files changed

- `sites/fullpotential-com/index.html`
- `sites/fullpotential-com/coracommons/index.html`
- `tools/public_site/test_cora_commons_front_door.py`
- `core/BUILD/specs/SPEC_cora-commons-front-door.md`
- `core/BUILD/results/SPEC_cora-commons-front-door.result.md`

## Proof

- Three focused unit tests pass for homepage routes, Cora explanation, reward boundary and next steps.
- `git diff --check` passes.
- Local static previews of `/` and `/coracommons/` returned HTTP 200.
- Live `https://fullpotential.com/coracommons/` returned HTTP/2 200 after deployment.
- Live homepage contains `Explore Cora Commons`, `Start with something real`, Dream Big, and `https://zenvillagecr.com/book`.
- Production SHA-256 after deployment:
  - homepage: `9c65ba8411699aa99e324dfbd36dc7f2fa021c3fc653481d8cbee15415e31cfb`
  - Cora Commons: `3d5afafb76c116729261ddf6d0bd2cee3b45f1e88256c0b9f2345b830de635f2`

## Boundaries and risks

- The Cora Commons page is a static public invitation. It does not expose the local founding ledger or MCP adapter.
- Founding actions currently route to a public email address; conversion, response and participation are not yet verified.
- Automated browser visual inspection remained unavailable, so final human visual acceptance is still required.
- Search indexes may briefly show the previous homepage after deployment.

## Rollback

Restore `/opt/fpai/core/applications/website-ai/frontend/fullpotential-com/index-prev-20261012-cora-1328.html` over the live `index.html`. The backup checksum is `fd342c813a345a64f017241bb758783bc804acf8f7a12365592a647971535578`.

The new `coracommons/` directory can remain inert if its homepage links are rolled back; removing it is not required for a safe rollback.

## Next unlocked move

Watch which door people choose and ask the first Cora Commons prospects whether they understand the invitation and can identify a contribution without private coaching.
