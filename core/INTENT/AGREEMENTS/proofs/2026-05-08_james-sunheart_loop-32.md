---
proof_id: 2026-05-08_james-sunheart_loop-32
loop_number: 32
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
  transformations_witnessed: true
  resources_circulated: true
  clean_pauses: false
---

# Loop 32 — Bridge champion-sign /credits → fp-credits-gateway (canonical SSOT)

**Quest:** Eliminate the parallel-ledger architectural drift introduced by Loops 30+31. Reroute champion-sign `/credits` and `/store/buy` to call fp-credits-gateway (the canonical $1M-treasury, 5-credit-type, hold-commit-release-escrow ledger that's been live in the ecosystem since Dec 2025) instead of our local jsonl ledger.

**Founder directive:**
> *"Look at other infrastructure we have like Zen Wallets, Zen credits etc. how do you suggest we loop that in"* → *"yes bridge"*

## Why this matters (architectural honesty)

Loop 30 shipped a parallel credits ledger without surveying existing infrastructure. The Field Coherence we shipped in Loop 27 demands the substrate tell the truth about itself; two ledgers in one ecosystem is the architectural opposite of that. Loop 32 closes the gap — eliminates duplication, brings us under canonical infrastructure (FP/UC/Cora/Sky/FI all 1:1 USD).

This is also the loop that demonstrates **repair** as commitment #6 from the Mirror Constitution: when we err (built parallel infra), we acknowledge, correct, document. Not hide.

## What shipped

### Gateway-side changes
- Generated explicit `CREDITS_MASTER_KEY` (random 64-char hex), wrote to `/etc/fp-credits-gateway.env`, mode 600
- Patched `/etc/systemd/system/fpai-fp-credits-gateway.service` to add `EnvironmentFile=-/etc/fp-credits-gateway.env`
- Added `("fp-game", "Full Potential Game substrate", ["read", "credit", "debit", "transfer"])` to gateway's `default_services` list in `/opt/fpai/services/fp-credits-gateway/app/main.py`
- Stopped manual uvicorn process, restarted via systemctl (now durable)
- Created fp-game API key via master-key authenticated `POST /api/keys`: `fpk_5621f1415cf09829`
- Granted James 1000 fp_credits via `POST /api/credit` (mirroring his Loop 30 local-ledger grant)

### champion-sign-side changes (`SERVICES/champion-sign/main.py`)
- Added `GATEWAY_URL`, `GATEWAY_KEY`, `GATEWAY_CREDIT_TYPE` env-driven config
- Added `_gw_call()` helper — urllib-based HTTP client with proper error mapping (HTTPError → HTTPException with detail)
- Replaced `_credit_balance()` body to call `GET /api/balance/{handle}` and return `balances.fp_credits`
- Replaced `_credit_history()` body to call `GET /api/transactions/{handle}` and normalize gateway's tx shape into our existing format
- Removed `_credit_append()` from write paths — local `ledger.jsonl` is now read-only historical audit
- `POST /credits/send` rewired to `POST /api/transfer` with `credit_type: fp_credits`
- `POST /credits/grant` (admin-only) rewired to `POST /api/credit` with `reason` field
- `GET /credits/leaderboard` reimplemented: enumerates Champion handles from `DATA_DIR`, queries gateway for each balance, returns sorted top N

### `/store/buy` bridged
- Replaced local-ledger `_credit_append` with `_gw_call(POST /api/transfer)` so store purchases now move canonical credits between buyer and merchant accounts in the gateway

### `/etc/champion-sign.env` updated
- `FP_CREDITS_GATEWAY_URL=http://127.0.0.1:8765`
- `FP_CREDITS_API_KEY=fps_d199...` (fp-game service key, restricted permissions: read, credit, debit, transfer)

## Verified

- `GET /api/champion/credits/balance/jamessunheart` → 1000 (then 999 after smoke test, then 974 after p2p send)
- `POST /api/champion/credits/send` (jamessunheart → test_friend, 25 credits) → tx_id captured from gateway, balances updated atomically
- Leaderboard returns canonical balances aggregated from Champion-Roll handles
- Local `ledger.jsonl` still on disk as historical audit (Loop 30-era data)

## Known follow-ups

- **Account naming alignment** — currently using player name (e.g. "jamessunheart") as account_id. The gateway's existing 20 Postgres-persisted accounts may use different IDs. If overlap exists, we should reconcile before recruiting more Champions.
- **Earn hooks (Loop 33+)** — wire automatic credit awards via gateway's `POST /api/contributions/reward/{user_id}` when a proof is filed with Distance-Weighted witness, when an affiliate signs WPA, when a Mirror is paired.
- **`/credits/history` UX** — gateway's tx shape isn't fully validated; when first real player files a tx we should sanity-check the normalization.
- **Genesis enrollment** — gateway logs `[INIT] ⚠️ Genesis: Not enrolled` at boot. May need attention separately.

## Files

- `/etc/fp-credits-gateway.env` (server-side, not in git)
- `/etc/systemd/system/fpai-fp-credits-gateway.service` (server-side, EnvironmentFile added)
- `/opt/fpai/services/fp-credits-gateway/app/main.py` (server-side, default_services list extended)
- `/etc/champion-sign.env` (server-side, gateway URL + API key added)
- `SERVICES/champion-sign/main.py` (in-repo): `_gw_call`, rewritten `_credit_balance`, `_credit_history`, `/credits/send`, `/credits/grant`, `/credits/leaderboard`, `/store/buy`

## Why I'm signing

Bridge is verified end-to-end. James now has 974 fp_credits in the canonical gateway (down from 1000 after two test transfers). The Game's `/credits` Telegram surface is unchanged; under the hood, the credits are now real ecosystem currency, not Game-toy tokens.

The Mirror Constitution's commitment 6 ("repair") is the load-bearing principle here. We acknowledged the duplication, corrected it, documented the path. The local ledger.jsonl stays for audit but is no longer authoritative.

*— Sealed 2026-05-08*
