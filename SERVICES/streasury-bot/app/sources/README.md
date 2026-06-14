# Source adapters

> **Purpose:** every external place we pull numbers from (banks, cards, Stripe,
> Wise, exchanges, on-chain wallets, Actual Budget, …) is implemented as an
> adapter that writes into `streasury.txn` with a unique `(source, source_ref)`
> tuple per external transaction.

## Why this shape

- **Idempotent.** Re-running a sync inserts only new rows; the
  `(tenant_id, source, source_ref)` unique index handles dedup.
- **Pluggable.** Adding a new source is one file. No special-cases in handlers
  or AI code — they just read from `streasury.txn` regardless of provenance.
- **Observable.** `streasury.source_connection.last_sync_*` columns make it
  trivial to surface "Stripe sync failed 6 hrs ago" in `/health` and Telegram.
- **Tenant-aware.** Every row is written with `tenant_id`, so the same adapter
  serves N customers cleanly when we productize.

## The contract

```python
# app/sources/<kind>.py

from dataclasses import dataclass
from app.sources.base import Adapter, SyncResult, SourceConnection

class StripeAdapter(Adapter):
    kind = "stripe"

    async def sync(self, conn: SourceConnection) -> SyncResult:
        # 1. read config (which date range, which currency, …)
        # 2. fetch from external API using conn.secret
        # 3. for each external txn, call ledger.insert_txn(...) with:
        #       source = self.kind
        #       source_ref = <external unique id>
        #       tenant_id = conn.tenant_id
        # 4. return SyncResult(seen=N, inserted=M, skipped=K, error=None)
```

A nightly cron job iterates `streasury.source_connection WHERE enabled = TRUE`,
loads the adapter for its `kind`, calls `sync(conn)`, and updates
`last_sync_*`. That's it.

## Adapters by phase

| Phase | Adapter | Coverage | Cost | When to build |
|---|---|---|---|---|
| **Phase 2** | `actual.py` | Reads everything Actual Budget pulled (which is itself fed by SimpleFIN/GoCardless) | Actual: $0; SimpleFIN: $15/yr | First, after Phase 1 dogfood week |
| **Phase 2** | `simplefin.py` | Direct US bank/card sync if not using Actual | $15/yr | Only if we choose direct over Actual |
| **Phase 2.5** | `stripe.py` | Stripe charges, payouts, fees, refunds | $0 (your Stripe API key) | When you have Stripe revenue worth tracking |
| **Phase 3** | `gocardless.py` | EU/UK PSD2 banks via Open Banking | Free up to 50 accounts | First non-US customer |
| **Phase 3** | `wise.py` | Multi-currency Wise account | $0 | Wise users |
| **Phase 3** | `digitalocean.py` | Server costs → recurring obligations | $0 | First month of real DO bills |
| **Phase 3** | `coinbase.py` / `kraken.py` (via CCXT) | Centralized exchange holdings | $0 | Crypto-native users |
| **Phase 3** | `solana.py` / `evm.py` | On-chain wallet balances + tx history | $0 (public RPC) | Hold real on-chain assets |
| **Phase 4** | `plaid.py` / `teller.py` | Premium US bank coverage | ~$0.30/account/mo | Customer needs a bank not on SimpleFIN |
| **Phase 4** | `pdf.py` | PDF statement parser (pdfplumber + AI normalize) | $0 | Customer with no API at their bank |

## Why Actual Budget is the centerpiece

Actual handles what's hard about ledger management — dedup, categorization
learning, transfers, splits, multi-currency, reconcile-against-bank. We don't
replicate it; we read from it and let it do the work.

So `actual.py` is the most important adapter. It's how a "log it on Telegram"
system inherits a battle-tested ledger for free.

## Testing an adapter

Each adapter must ship with a `tests/test_<kind>.py` that:

1. Reads a recorded fixture (a real API response saved as JSON, scrubbed of
   secrets).
2. Runs `sync()` against a temp DB.
3. Asserts the right rows landed in `streasury.txn`.
4. Re-runs `sync()` and asserts no duplicate rows (idempotency check).

We're not building tests in Phase 1 — we're dogfooding on real data first.
But every Phase 2+ adapter must have these tests before merge.

## Beta-tester invariants

These cannot regress while the bot has real money in it:

1. **Never invent transactions.** If an API returns ambiguity, we record the
   raw payload in `import_batch.notes` and ask via Telegram before writing.
2. **Idempotent sync.** Running the same sync twice = exactly the same
   ledger. Enforced by the unique index, not by adapter cleverness.
3. **No silent failures.** If a sync errors, `last_sync_error` is set AND the
   bot sends a Telegram message tomorrow morning ("Stripe sync failed
   yesterday — last successful: 2 days ago").
4. **Read-only by default.** Adapters MUST NOT initiate any payment, transfer,
   or write to the external system. We're a reporting tool, not a money
   transmitter. (See PRODUCT_VISION.md: "Don't become a regulated entity.")
