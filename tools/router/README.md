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

Run one guarded write:

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

## What It Will Not Do

- Move money or resources.
- Send outreach or public messages.
- Deploy production.
- Touch secrets.
- Stop, move, delete, or archive services.
- Make doctrine, people, treasury, offer, legal, or irreversible choices.

Those route back to James/Ember.

## Phone / Cloud Note

Phone/cloud Codex can use the router from GitHub state only. If the vault is not
available, the router falls back to `docs/codex/INTENT_BUILDSTREAM.md`. Vault
writes still route through Ember/Claude Code.
