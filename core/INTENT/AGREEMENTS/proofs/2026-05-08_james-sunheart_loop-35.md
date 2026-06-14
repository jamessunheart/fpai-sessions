---
proof_id: 2026-05-08_james-sunheart_loop-35
loop_number: 35
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
  resources_circulated: false
  clean_pauses: false
---

# Loop 35 — `/store post` multi-step bot flow

**Quest:** Add a Telegram-native multi-step flow for posting store offers, so non-technical Champions can list services from their phone without curl or the web form.

**Founder directive:**
> *"Please continue building"* — picking up from the queue.

## Note on intended Loop 35 (deferred)

Loop 35 was originally planned as Hold-Commit-Release escrow for Mirror first-proof witnessing, using fp-credits-gateway's `/api/transact/hold` + `/commit` + `/release`. During implementation I found:

1. The hold endpoint uses `wallet_id` semantics that diverge from the `account_id` we'd been using — calling hold with `from_wallet_id: jamessunheart` returned "Insufficient balance. Has 0.0, needs 10.0" despite his account_id having 979 fp_credits. There appears to be a wallet/account separation in the gateway's data model not surfaced by /api/balance.
2. The escrow has no real test case until Mirror #1 is paired and a first proof is filed for witnessing.

Rather than ship theoretical infrastructure with an unresolved naming-model bug, I deferred the escrow loop. It remains queued; will revisit when Mirror #1 exists and the wallet_id semantics are clarified by the gateway maintainer or by deeper code reading.

## What shipped instead

### Multi-step `/store post` flow in fp-game-bot
Five conversational steps:
1. **Title** (2–120 chars)
2. **Description** (≤2000 chars, or `skip`)
3. **Price in credits** (integer, or `0` for USD-only)
4. **Price in USD** (number, or `0` for credit-only) — must have at least one of #3/#4
5. **URL** (must start with http:// or https://, or `skip`)

On successful post, replies with the assigned `offer_id`, the tier the gateway placed it in (💎/⚖️/💵), and the credit_share weight, plus a link to /game/store. Channels naturally toward credit-only listings via the closing tip.

### Help text + dispatch
- WELCOME message updated: `/store — marketplace · /store post to list · /store buy <id> to purchase`
- `STATE[chat_id] = {"flow": "store", ...}` integrated into the existing FLOW_HANDLERS dispatch alongside sign/card/proof.
- `/cancel` aborts cleanly at any step (already handled by the global cancel command).

## Why this matters

Until now, listing an offer required curl or the web form. Anyone selling something through Telegram (which the bot's voice-and-direct-messaging UX is naturally suited to) had no way to list. Loop 35 closes that gap — a Champion can `/store post` from their phone in 60 seconds, and the offer goes live with the same tier ranking the web form uses.

The substrate now lets any Champion both **buy** (`/store buy <id>`) and **list** (`/store post`) from Telegram. The marketplace is fully phone-native.

## Verified

- Service deploys cleanly (syntax OK, restart healthy)
- `STATE`/`FLOW_HANDLERS` dispatch verified by code inspection — store flow follows the exact same pattern as sign/card/proof, which are battle-tested

## Files

- `SERVICES/fp-game-bot/main.py` — `cmd_store` "post" subcommand entry, `handle_store_step` (5-step flow), FLOW_HANDLERS entry, WELCOME help text update

## Next loops

- **Loop 36** — Hold-Commit-Release escrow for Mirror first-proof (re-attempted with wallet_id semantics resolved). Gates on either reading more gateway code or having a Mirror #1 paired to test against.
- **Loop 37** — Account-naming reconciliation against gateway's 20 pre-existing Postgres accounts.

*— Sealed 2026-05-08*
