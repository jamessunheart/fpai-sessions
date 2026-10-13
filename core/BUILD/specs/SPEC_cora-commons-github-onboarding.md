# SPEC — Cora Commons GitHub onboarding

**Approved by:** James Sunheart in the active Codex task on 2026-10-13  
**Branch:** `feat/cora-commons-front-door`

## Intent

Turn the existing Cora Commons public explanation into a working builder entrance: the FullPotential homepage introduces the Commons, the Cora page explains exactly how a human and their chosen agent can connect, and a dedicated public GitHub repository provides the canonical founding direction, open needs and contribution pathway.

## Files allowed

- `sites/fullpotential-com/index.html`
- `sites/fullpotential-com/coracommons/index.html`
- `tools/public_site/test_cora_commons_front_door.py`
- `core/BUILD/specs/SPEC_cora-commons-github-onboarding.md`
- `core/BUILD/results/SPEC_cora-commons-github-onboarding.result.md`
- `core/BUILD/REGISTRY.json`
- External staging directory `../cora-commons-github/`

## Boundaries

- GitHub is the public build and evidence surface, not the treasury or private beneficiary database.
- Do not expose the local SQLite ledger, access codes, credentials, private bills or treasury controls.
- Do not imply uploads, issues, commits or pull requests automatically earn CORA or fiat.
- Keep independent review and human authority visible.
- Do not deploy website links until the target repository resolves publicly.
- Repository creation may proceed only through the authenticated GitHub account; never choose an account or enter credentials for James.

## Definition of done

- A dedicated `jamessunheart/cora-commons` public repository exists with orientation, agent instructions, governance, reward boundaries, a first open Need and contribution templates.
- The FullPotential homepage links clearly to the Cora explanation.
- The Cora page gives a three-step GitHub onboarding path and direct links for needs, builders and agents.
- Automated checks pass.
- Production is backed up, deployed narrowly and returns HTTP 200 with working GitHub links.
