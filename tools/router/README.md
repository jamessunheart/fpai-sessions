# Router

`tools/router/route.py` is the guarded Rung 3 auto-routing slice.

It reads the weighted `<!-- INTENTS -->` block from the vault Intent Buildstream,
falls back to the repo mirror, chooses the highest-weighted `ready` intent, and
advances exactly one safe step.

## Safe Commands

Report only:

```bash
python3 tools/router/route.py --dry-run
```

Run one guarded write. This only acts on intents explicitly marked
`route:auto`; `route:ember`, `route:codex`, `route:api`, `route:james`, and
missing routes escalate instead of drafting or building.

```bash
python3 tools/router/route.py --apply
```

Run tests:

```bash
python3 -m unittest tools.router.test_route
```

## What It Can Do

- Draft one new `docs/codex/specs/SPEC_<slug>.md` with `status: needs-bless`.
- Request a James/Ember bless when a spec exists but is unblessed.
- Route a blessed spec for Codex build.
- Optionally append a note to the Codex-owned handoff lane.

Only `route:auto` intents are eligible for those actions.

## Conscious Routing Contract

Every router output and optional handoff note carries the same four fields:

- `Aware` — what the router noticed in the current state.
- `Aligned` — which adjacent downstream intent the action serves.
- `Care` — what risk, cost, James-state, or boundary is protected.
- `Proof` — what consequence can be checked on the next loop.

This keeps automation from becoming "can I do this?" and forces the better
question: "should this be routed, now, by whom, at what cost, for what becoming?"

## What It Will Not Do

- Move money or resources.
- Send outreach or public messages.
- Deploy production.
- Touch secrets.
- Stop, move, delete, or archive services.
- Make doctrine, people, treasury, offer, legal, or irreversible choices.

Those route back to James/Ember.

It also will not auto-act on builder-routed intents. `route:ember`,
`route:codex`, and `route:api` are reported/escalated to that lane; missing
route metadata is treated as unsafe until clarified.

## Phone / Cloud Note

Phone/cloud Codex can use the router from GitHub state only. If the vault is not
available, the router falls back to `docs/codex/INTENT_BUILDSTREAM.md`. Vault
writes still route through Ember/Claude Code.
