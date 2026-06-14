---
proof_id: 2026-05-08_james-sunheart_loop-30
loop_number: 30
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

# Loop 30 — /credits substrate · Coherent Credit ledger v0

**Quest:** Bootstrap the Coherent Credit substrate as a separate currency from Field Score points. Players start at 0 and must earn or be granted credits. Architect mints via admin endpoint. Peer-to-peer send. Public leaderboard.

**Founder directive:**
> *"Players start with 0 balance, must earn it or top up to get credits. Points can be based on completion of things but not the same as whats in someones wallet.. points can convert to bonuses within game etc. but different."*

## What shipped

### Append-only ledger at `/var/lib/full-potential/credits/ledger.jsonl`
Three transaction kinds: `grant` (architect), `send` (peer), `earn` (gameplay hooks — Loop 32). Balance computed by reading entire ledger (audit-friendly, no sync issues).

### Endpoints
- `GET /credits/balance/{handle}` — public read
- `GET /credits/history/{handle}` — public history with directions, memos, kinds
- `POST /credits/send` — peer-to-peer (rejects self-send, insufficient balance returns 400)
- `POST /credits/grant` — admin-only (X-Admin-Token), mints credits
- `GET /credits/leaderboard` — top holders + total in circulation

### Telegram commands (`/credits`)
- `/credits` → balance + last 5 transactions
- `/credits send 10 to @bob memo here` → peer transfer
- `/credits history` → last 20
- `/credits leaderboard` → top 10 holders

### Genesis grant
James granted 1000 credits as founding balance for testing the store flow.

## Architecture decision: credits ≠ points

Field Score (points) and Credits (wallet) are separate ledgers. Points reward participation (1·champ + 1·card + 2·proof + 3·affil = vanity participation metric). Credits are real economic value exchanged in /store. This separation lets us tune incentives independently — e.g., points can convert to bonuses without inflating credit supply.

## Files

- `SERVICES/champion-sign/main.py` — `_credit_balance`, `_credit_history`, `_credit_append`, `_norm_handle`, `CreditSend`, `CreditGrant`, 5 endpoints
- `SERVICES/fp-game-bot/main.py` — `cmd_credits` (4 subcommands), help text update

*— Sealed 2026-05-08*
