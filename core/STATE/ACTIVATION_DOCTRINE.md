# ACTIVATION DOCTRINE — turning inert builds into live value

**Status:** canonical · authored 2026-07-05 (James: "activate, and create rules/principles and autonomy for activation") · formalizes the *activate* half of [`SPEC_d188`](../BUILD/specs/SPEC_d188_build-loop-activation-audit-act.md) · pairs with `memory/feedback_activation_is_the_bottleneck.md`.

## Why this exists

The build loop is prolific and the reserved walls are correct — but the result was **34 merged builds sitting INERT** (built · reviewed · merged · wired to nothing live). Building stopped being the constraint; **activation** — wiring a reviewed build to a live, customer-reachable surface — became it. This doctrine gives the substrate **bounded autonomy to activate**, so value crosses the last inch without waiting on a James-hand every time, while keeping the money/voice/new-human/irreversible walls intact.

## Definitions

- **Inert build** — merged to `feat/headless-build`, independently reviewed, but not reachable by any real user (library/sandbox, `live_send=false`).
- **Activation** — wiring an inert build to a live surface a real person can reach (a live bot handler, a deployed endpoint, an enabled feature flag) so it produces a real result.
- **Activation ledger** — append-only JSONL of every activation (what · when · surface · rollback path · kill-switch), so the substrate can never be surprised by its own live footprint. Path: `~/.config/fpai/activation/ledger.jsonl`.

## The Activation Trust Tier — AUTO-ACTIVATE (substrate, no James) requires ALL of:

1. **Reviewed** — the build already passed independent AI review + merged (never activate an unreviewed build).
2. **Reversible in one move** — a documented rollback + a kill-switch file (`touch <flag>` disables it). No activation without a kill-switch.
3. **$0 marginal or within the standing $20/day cap** — uses the subscription/CLI path, not a new metered spend.
4. **Opt-in surface only** — the user initiates (inbound bot message, a page they chose to open). NEVER cold/first outbound to a new human.
5. **No money** — no charge, payment, price, or commitment created.
6. **Existing credentials only** — no new secret, phone number, paid account, or security-config change.
7. **Not main / not treasury / not security-config / not the identity stack.**
8. **Logged** — an activation-ledger row written before the surface goes live.

If all 8 hold → the substrate activates and logs it. Reversible + bounded + opt-in + $0 = the same logic as reversible-auto-exec, extended to the live surface.

## RESERVED — James only (any one triggers):

- First outbound contact to a new human · any cold outreach.
- Money: charging, paying, pricing, financial commitment.
- A new credential / live phone number / new paid account / ad spend.
- Public content in James's personal voice.
- Security config · `main` · treasury moves · the identity stack.
- Any effect that is irreversible or hard to reverse externally.

Draft autonomous, ship reserved: the substrate prepares the reserved activation (config, copy, wiring) and surfaces a one-tap APPROVE to James — it does not cross the wall itself.

## The Activation Arm (autonomy mechanism)

Counterpart to the build loop. After a build merges, an **activation pass** evaluates it against the 8 gates:
- **PASS all 8** → auto-activate, write ledger row, register kill-switch, emit one digest line.
- **RESERVED** → stage the activation + queue a one-tap APPROVE card to James (via `feed_decision.sh`).
- **Not activatable** (pure library/no live surface) → mark `inert-by-design` in the audit so it stops counting as a stalled build.

Global kill-switch: `touch /opt/fpai-build/.activation_disabled` halts all auto-activation. Every activation is independently reversible via its own kill-switch too.

## First activation (2026-07-05) — the reference case

**d203 chat-based-assessment** built the chat endpoint `POST /api/champion/lead/assessment-chat` into `SERVICES/champion-sign/main.py`, merged on 162. But the live `champion-sign` service on the web host (198.54.123.234) runs **stale code** — the endpoint returns **404** live while old `/lead/submit` returns 200. Classic inert gap: merged ≠ deployed.

- **Activation = the canonical deploy:** `bash SERVICES/champion-sign/deploy.sh` (rsync main.py → 198, restart service, health-check). Idempotent, tested, reversible (restart = kill-switch; redeploy prior `main.py` to roll back).
- **Gate check:** reviewed ✅ · reversible ✅ · $0 ✅ · opt-in surface (user POSTs from the page) ✅ · no money ✅ · existing deploy key ✅ · not main/treasury/security/identity ✅ · ledger-logged ✅ → **passes all 8**.
- **But it deploys to the live prod web host**, so the harness classifier holds it for an explicit James OK the first time. This is exactly the reserved edge the Activation Arm should learn: once James blesses "deploy champion-sign," a reviewed re-deploy of the *same* service is auto-activatable; a *new* service/host stays reserved.
