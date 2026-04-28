"""app/sources/ — pull adapters for external financial data.

Each adapter has the same shape:

    class Adapter:
        kind: str                   # "simplefin" / "stripe" / "actual" / ...

        async def sync(self, conn: SourceConnection) -> SyncResult:
            ...

`SourceConnection` is a row from streasury.source_connection (kind, label,
secret, config). Adapters write transactions back into the ledger via
`app.ledger.insert_txn` with `source=self.kind` and `source_ref=<external id>`.
The unique index on (tenant_id, source, source_ref) guarantees idempotent sync.

See app/sources/README.md for the full adapter pattern + roadmap.
"""
