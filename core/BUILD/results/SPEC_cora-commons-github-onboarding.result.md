# Result — Cora Commons GitHub onboarding

**Date:** 2026-10-13  
**Branch:** `feat/cora-commons-front-door`  
**Status:** deployed and publicly verified

## Intent solved

FullPotential.com now introduces Cora Commons and routes people to a clear connection path. The Cora page explains how a human and their chosen agent can read the shared direction, choose a need, fork safely and submit a contribution for independent review.

## Canonical public surfaces

- Introduction: `https://fullpotential.com/coracommons/`
- Builder repository: `https://github.com/jamessunheart/cora-commons`
- Agent instructions: `https://github.com/jamessunheart/cora-commons/blob/main/AGENTS.md`
- First founding contribution: `https://github.com/jamessunheart/cora-commons/issues/1`

## Repository contents

The dedicated public repository contains README, vision, agent instructions, contribution protocol, founding governance, reward boundaries, MIT license, Needs, BRICKS, contribution receipts and GitHub issue/pull-request templates. Local source commit: `d458167`.

## Website files changed

- `sites/fullpotential-com/index.html`
- `sites/fullpotential-com/coracommons/index.html`
- `tools/public_site/test_cora_commons_front_door.py`
- `core/BUILD/specs/SPEC_cora-commons-github-onboarding.md`
- `core/BUILD/results/SPEC_cora-commons-github-onboarding.result.md`
- `core/BUILD/REGISTRY.json`

## Proof

- Four focused homepage/Cora tests pass.
- Both HTML files parse without syntax errors through Python's HTML parser.
- Registry JSON validation and `git diff --check` pass.
- GitHub connector read-back confirms the repository is public on default branch `main` and exposes README, AGENTS and the Need issue form.
- Live homepage, Cora page, repository, AGENTS page and Need form all returned HTTP 200 after deployment.
- Live website contains `Build Cora`, `Understand it and connect your agent`, `Connect through GitHub` and the canonical repository links.
- Production SHA-256 after deployment:
  - homepage: `beafde6775e183a613eab040bb888481972afbc75072eba608e33ad1d239cef9`
  - Cora Commons: `4b301f9ac4413401c84e4d970d43e7e16dbfdfe2be59ebe841cc602f99083df0`

## Boundaries and risks

- GitHub is the public build/evidence surface, not the treasury, CORA ledger or private beneficiary system.
- GitHub account identity is real enough for attribution but does not prove legal identity or human presence.
- The reward mechanism remains provisional; issue #1 explicitly offers recognition only and no funded CORA or fiat reward.
- Firefox visual QA confirmed the live desktop page renders clearly: the primary invitation, Cora Loop and agent connection path are visible without overlap or clipping. The in-app browser itself remained unavailable for this check.

## Rollback

On production host `198.54.123.234`, restore:

- `index-prev-20261013-cora-github.html` over `index.html`
- `coracommons/index-prev-20261013-cora-github.html` over `coracommons/index.html`

Backup SHA-256 values match the pre-deployment production files:

- homepage: `9c65ba8411699aa99e324dfbd36dc7f2fa021c3fc653481d8cbee15415e31cfb`
- Cora Commons: `3d5afafb76c116729261ddf6d0bd2cee3b45f1e88256c0b9f2345b830de635f2`

## Downstream intent unlocked

A friend can now enter through the public website, give their agent the canonical instructions and attempt one real contribution loop. The next proof is whether they can complete issue #1 without private founder coaching.
