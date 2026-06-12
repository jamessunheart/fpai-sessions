"""app/sources/stripe.py — Stripe charges + payouts + fees.

PHASE 2.5 STUB. Pulls from Stripe's API into the ledger. Useful even if you
don't sell heavily through Stripe, because it gives clean revenue/refund/fee
attribution that bank feeds don't (banks see the net deposit only).

Plan:
    1. conn.secret = restricted Stripe API key (read-only on Charges +
       BalanceTransactions).
    2. List BalanceTransactions since conn.config["since"]; each has:
           - id (use as source_ref)
           - type (charge / refund / payout / payout_fee / stripe_fee / ...)
           - amount, currency, created
           - source (charge id) for joining to customer email if desired
    3. Map type → category:
           charge       → "revenue"
           refund       → "revenue" (negative)
           payout_fee / stripe_fee → "ai" wait no — "stripe_fees"
           ...
    4. ledger.insert_txn for each.
    5. conn.config["since"] = now.

Docs: https://docs.stripe.com/api/balance_transactions/list
"""
from __future__ import annotations

from .base import Adapter, SourceConnection, SyncResult, register


class StripeAdapter(Adapter):
    kind = "stripe"

    async def sync(self, conn: SourceConnection) -> SyncResult:  # pragma: no cover (stub)
        return SyncResult(
            seen=0, inserted=0, skipped=0,
            error="stripe adapter not yet implemented (Phase 2.5)",
        )


register(StripeAdapter())
