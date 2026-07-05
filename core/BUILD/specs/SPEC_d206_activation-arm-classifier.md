# SPEC d206 — Activation Arm classifier (make the 8-gate doctrine executable)

**Why (James 2026-07-05, "autonomy for activation"):** `core/STATE/ACTIVATION_DOCTRINE.md` defines 8 auto-activate gates + reserved walls, but nothing applies them. Meanwhile `activation_audit.py` reports "34 inert" — inflated, because it can't tell **inert-by-design** (docs · benchmarks · policy · internal ledgers — nothing to activate) from **built-but-not-shipped** (a real live surface running stale/absent). Manual classification (2026-07-05) found only ~9 of 34 have a live surface and ~3 touch value (d196 meta-attribution · d163 bot-LLM · d011/d122 correction-injector). The Arm makes this automatic and turns the audit into an action queue.

## Design (LIBRARY + CLI — classify + stage only, does NOT cross the wall)

Create `tools/build_loop/activation_arm.py`:
1. For each merged build, read its `core/BUILD/results/<spec>.result.md` + changed-file list and classify the live surface: does it add/modify a `SERVICES/*` endpoint, a systemd `.service`, a bot handler, a deploy script, or an nginx route? If none → **inert-by-design**.
2. Apply the 8 doctrine gates to the activatable ones → bucket each as **AUTO** (all 8 pass · reversible · $0 · opt-in · no-money · existing-creds · not-main/treasury/security/identity · reviewed), **RESERVED** (any reserved trigger — prod deploy first-bless · new cred · money · new-human · public-voice), or **INERT-BY-DESIGN**.
3. Emit `~/.config/fpai/activation/queue.json`: the ranked activation queue (AUTO first, then RESERVED with a one-line "why + exact command", inert-by-design collapsed to a count). Value-tagged builds (funnel/bot/conversation) rank above internal ones.
4. Feed the audit: builds classified inert-by-design are marked so `activation_audit.py` stops counting them as stalled (the number finally tells the truth).
5. NO activation performed. AUTO items produce a ready command + ledger-row stub; a later spec (or James's bless) executes. RESERVED items stage a one-tap APPROVE card via `feed_decision.sh`.

## Guardrails

- Classify + stage only. Never deploy, restart a live service, push, merge, touch secrets, or move money. Reversible (pure analysis + a queue file). The cross-the-wall executor is a separate, separately-reviewed spec.
- Read the doctrine's 8 gates from `ACTIVATION_DOCTRINE.md` as the source of truth (don't hardcode a drifting copy).

## Contract

Adds `tools/build_loop/activation_arm.py` + tests; updates `activation_audit.py` to honor inert-by-design. Register in `REGISTRY.json`. Independent review. Do NOT push or merge.

## Done / Proof

`python3 tools/build_loop/activation_arm.py` writes `queue.json` where the current 34 "inert" builds resolve to ~22 inert-by-design (collapsed to a count), ~9 activatable, with d196/d163/d011 ranked top as RESERVED-value items carrying their exact deploy command. `activation_audit.py` unexplained-inert count drops to only genuinely-stalled live surfaces. Tests: a doc-only build → inert-by-design; a SERVICES endpoint build → activatable; a prod-deploy build → RESERVED with command.

## Context

- Doctrine: `core/STATE/ACTIVATION_DOCTRINE.md` · `memory/feedback_activation_is_the_bottleneck.md` · builds on d188 (audit) + d194 (orchestrator seeds).
- First activation reference: d203 champion-sign chat endpoint (`bash SERVICES/champion-sign/deploy.sh`) — RESERVED first-bless, then auto on re-deploy.
