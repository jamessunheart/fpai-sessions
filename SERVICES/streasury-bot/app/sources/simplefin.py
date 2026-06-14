"""app/sources/simplefin.py — direct SimpleFIN Bridge pull (alternative to Actual).

PHASE 2 STUB. SimpleFIN is the cheap, contract-free option for US/CA banks
and cards. Most users will use it via Actual (which has built-in SimpleFIN
support), but a direct adapter is useful when:
    - the user doesn't want to run Actual at all (lighter footprint), or
    - they want a transaction in our ledger before Actual's nightly sync.

SimpleFIN Bridge ($15/yr per end-user) gives:
    - A setup token. The user exchanges it for an access_url at
      https://bridge.simplefin.org/simplefin/claim/<token>.
    - access_url has the shape https://USER:PASS@beta-bridge.simplefin.org/...
    - GET access_url + /accounts returns JSON: accounts + nested transactions.

Plan:
    1. conn.secret = access_url
    2. GET access_url + "/accounts?start-date=<since>"
    3. For each account, ensure it exists in streasury.account.
    4. For each transaction, call ledger.insert_txn(source="simplefin",
       source_ref=transaction.id, ...).
    5. conn.config["since"] = now - 1 day (small overlap to catch late posts).

Docs: https://www.simplefin.org/protocol.html
"""
from __future__ import annotations

from .base import Adapter, SourceConnection, SyncResult, register


class SimpleFinAdapter(Adapter):
    kind = "simplefin"

    async def sync(self, conn: SourceConnection) -> SyncResult:  # pragma: no cover (stub)
        return SyncResult(
            seen=0, inserted=0, skipped=0,
            error="simplefin adapter not yet implemented (Phase 2)",
        )


register(SimpleFinAdapter())
