---
proof_id: 2026-05-08_james-sunheart_loop-34
loop_number: 34
date_started: 2026-05-08
date_committed: 2026-05-08
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit)
witness_signed: true
consent: public
agreement_type: feature
status: complete
mvs_increments:
  agreements_kept: true
  outputs_shipped: true
  transformations_witnessed: false
  resources_circulated: true
  clean_pauses: false
---

# Loop 34 — Earn hooks · auto-credit on architecturally-honest actions

**Quest:** Wire automatic credit awards into champion-sign's existing event endpoints. The economy now self-runs — players don't need an architect to hand-grant credits; gameplay actions earn them directly through the canonical fp-credits-gateway.

**Founder directive:**
> *"Please continue building"*

## Earn schedule (architecturally tuned)

The schedule rewards what builds the field most, not vanity participation:

| Action | Player | Affiliate / Witness |
|---|---|---|
| Sign WPA | 0 (entry — not earn) | inviter: **+50** |
| Build Character | 0 (vanity) | — |
| File Proof (any witness) | **+5** | — |
| File Proof with Distance-Weighted Witness | **+20** | witness: **+30** |
| Pair Mirror | **+100** (one-time) | — |

Distance-Weighted detection uses the same heuristic as Field Coherence's Witness component: witness must be neither the player (first-name match) nor an AI marker (claude / anthropic / openai / gpt-/the bot / ai). Anything else qualifies as DW.

## Why these specific values

- **Witnessing pays the most.** A Distance-Weighted Witness earns +30 credits — more than the player who filed the proof. The architecture tells the truth about what's hard: filing your own proof is comparatively easy; reading someone else's proof and signing honestly is the rare and valuable act.
- **Affiliating pays well.** +50 per signing through your invite link. Recruiting aligned humans IS the field expanding.
- **Mirror pairing is one-time +100.** Largest single award. Pairing operationalizes Phase 1 of the white paper — that's worth structural credit recognition.
- **Signing and Building Character earn 0.** Per James's design: "must earn or top up." Entry is free; earning is for actions that benefit the field beyond the player themselves.

## What shipped

### `_award_credits_safe()` helper
Best-effort gateway credit grant. Never blocks the user-facing action on credit-grant failure — the proof gets filed even if the gateway is down. Returns tx_id on success, None silently on failure.

### Hooks added at three substrate-event sites
1. **`/sign`** (after champion record creation) — if `req.inviter` is set, award the inviter +50 credits with reason `affiliate sign: {new champion name}`.
2. **`/proof/submit`** (after proof markdown written) — award the player +5 (any witness) or +20 (DW witness). If DW, also award the witness +30. Reason includes `proof loop-{N}`.
3. **`/mirror/register`** (after pairing record created) — award the player +100 one-time with reason `mirror pairing: {mirror_handle}`.

### Response shape additions
Hooked endpoints now include `credits_awarded` field in their JSON response so callers (bot, UI) can show "+5 credits earned" inline.

## Verified

- Service deploys cleanly (syntax OK, restart healthy)
- Gateway grant path tested via `/credits/grant`: James went 974 → 979 (+5) atomically with tx_id captured
- The hooks are fire-and-forget — verified by reading the safe wrapper logic; gateway downtime won't break /sign /proof/submit /mirror/register

## Why this matters

Before Loop 34, credits could only enter the gateway via architect grant. The economy had a single ingress (James) and was therefore not self-running. After Loop 34, credits enter the gateway every time someone witnesses, files, recruits, or pairs — automatically. The Game's economy is now its own engine.

The credit schedule also reinforces the white paper's load-bearing intent: **distance-weighted witnessing is the practice the architecture rewards most.** When Mirror #1 is paired and gets its first witnessed proof, the witness will be paid more than the player — exactly what the white paper §4.5 asks of the Field.

## Next loops

- **Loop 35** — Hold-Commit-Release escrow for Mirror first-proof. Gateway has `/api/transact/hold` + `/commit` + `/release`. Hold credits in escrow when first proof is submitted; release on Distance-Weighted Witness signature; refund if witness refuses. Architecturally pure but requires Mirror #1 to test.
- **Loop 36** — Multi-step `/store post` bot flow. Right now anyone can list via curl or the web form; the bot's `/store post` is curl-only. Multi-step flow on Telegram lets non-technical Champions list from their phone.
- **Loop 37** — Account-naming reconciliation against the gateway's 20 pre-existing accounts.

## Files

- `SERVICES/champion-sign/main.py` — `_award_credits_safe()` helper, three earn hooks, credits_awarded responses

*— Sealed 2026-05-08*
