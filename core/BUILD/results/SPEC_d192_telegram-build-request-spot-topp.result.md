# SPEC d192 — Spot & Topple next-domino loop

Status: done in working tree / awaiting review + merge.

build_kind: library

## Files Changed

- `tools/allocation/opportunity_engine.py`
- `tools/allocation/test_opportunity_engine.py`
- `core/BUILD/specs/SPEC_d192_telegram-build-request-spot-topp.md`
- `core/BUILD/results/SPEC_d192_telegram-build-request-spot-topp.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

- Added a read/rank/propose-only Next Domino layer to the Opportunity Intelligence Engine.
- Existing Opportunity Score, Allocation Score, and Closest-to-Cash rankings remain intact.
- Seeded opportunity rows now carry Spot fields: current constraint, value trapped, and smallest domino.
- Seeded opportunity rows now carry Topple fields: next action, gate, proof, and missing capability.
- Added `next_domino_score`, which rewards constraint/leverage/proof-speed/reversibility and penalizes James-reserved, human-edge, Ember-route, and missing-capability gates.
- CLI output, digest line, and council context now expose "Next Domino: Spot -> Topple -> Proof."

## Tests

- `python3 -B -m unittest tools.allocation.test_opportunity_engine tools.allocation.test_capability_ledger` — 11 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/allocation/opportunity_engine.py tools/allocation/test_opportunity_engine.py`
- `python3 tools/allocation/opportunity_engine.py --ledger /tmp/d192-opportunities.json`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d192_telegram-build-request-spot-topp --base-ref feat/headless-build --head-ref HEAD` — OK: build_kind=library declared
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d192-registry.json`
- `git diff --check`

## Proof

The CLI proof keeps the existing rankings while adding the next-domino view:

- Top by Allocation Score: Resource Optimization Audit.
- Top Next Domino: Opportunity Intelligence Engine.
- Opportunity Intelligence Engine status: `topple-ready`.
- Resource Optimization Audit status: `James-reserved`, so it is not treated as the easiest automatic next domino even though it is highest by allocation score.
- Capability-gap rows report "build capability first" rather than pretending they can be toppled.

## Risks

- Numeric seed scores are first-pass operating weights, not market facts.
- The gate penalty is intentionally conservative; James-reserved revenue actions can rank below reversible internal builds until James explicitly approves the human/public edge.
- This does not itself execute a Topple action; it only makes the next-domino recommendation visible to the existing council/allocation surfaces.

## Rollback

Revert this branch. No live service, deploy, outreach, treasury action, secret, or external API effect was performed.

## Intent Solved

The allocation engine can now distinguish "highest theoretical value" from "next safe domino" and shows Spot, Topple, proof, and gate status explicitly.

## Downstream Intent Unlocked

Council/router decisions can use a concrete next-domino signal before proposing builds, so future loops can ask "can we topple this now, or must we build a capability first?" without granting unsafe autonomous authority.
