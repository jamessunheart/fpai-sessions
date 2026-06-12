# Backup & restore

The deploy pipeline already invokes the `backup-restore` skill before each
deploy. To run a manual snapshot:

```bash
ssh-via-deploy.sh streasury-bot brain -- \
    pg_dump --schema=streasury "$DATABASE_URL" \
    | gzip > /opt/fpai/backups/streasury/$(date -u +%Y%m%dT%H%M%SZ).sql.gz
```

Or, equivalent, locally with the env file sourced:

```bash
source /etc/streasury-bot/streasury.env
pg_dump --schema=streasury "$DATABASE_URL" | gzip > backup-$(date -u +%Y%m%dT%H%M%SZ).sql.gz
```

## Restore (full schema)

⚠ RISKY: this drops every transaction added since the snapshot.

```bash
gunzip -c backup-2026-04-28T180000Z.sql.gz | psql "$DATABASE_URL"
```

The schema file uses `CREATE TABLE IF NOT EXISTS`, so re-running the schema
script after a restore is a no-op.

## Restore one row

If you misclick a confirm:

```sql
DELETE FROM streasury.txn WHERE id = <id>;
```

If you over-imported a CSV and want to roll back the whole batch:

```sql
DELETE FROM streasury.txn WHERE import_batch_id = <batch_id>;
UPDATE streasury.import_batch SET rows_inserted = 0 WHERE id = <batch_id>;
```
