# AppFlowy Backup + Restore Notes

The Brain's durable state is primarily:

- PostgreSQL: AppFlowy users, workspaces, rows, collab metadata
- MinIO volume: file/blob storage
- Config/secrets: nginx, Telegram env, MCP token mapping, service credentials

## Backup

Script source:

- Local: `docs/zen-village/runbook/backup_appflowy.sh`
- Server: `/opt/zen-village/scripts/backup-appflowy.sh`
- Off-host sync source: `docs/zen-village/runbook/sync_appflowy_backups_to_primary.sh`
- Off-host sync server path: `/opt/zen-village/scripts/sync-appflowy-backups-to-primary.sh`

Run:

```bash
ssh root@162.0.208.88 '/opt/zen-village/scripts/backup-appflowy.sh'
```

Output:

```text
/opt/zen-village/backups/appflowy/<timestamp>/
```

## Off-Host Copy

Backups are copied nightly from Secondary to Primary.

- Secondary source: `/opt/zen-village/backups/appflowy/`
- Primary destination: `root@198.54.123.234:/opt/zen-village/backups/appflowy/`
- Retention: 14 days on both hosts
- Service: `zv-appflowy-backup-sync.service`
- Timer: `zv-appflowy-backup-sync.timer`
- Schedule: daily `08:00 UTC` (`2am Costa Rica`)
- Log: `/var/log/zv-appflowy-backup-sync.log`

Run manually:

```bash
ssh root@162.0.208.88 '/opt/zen-village/scripts/sync-appflowy-backups-to-primary.sh'
```

Check timer:

```bash
ssh root@162.0.208.88 'systemctl list-timers --all zv-appflowy-backup-sync.timer --no-pager'
```

Each backup contains:

- `postgres.dump` — custom-format `pg_dump`
- `postgres_schema.sql` — schema-only dump
- `minio_data.tgz` — MinIO volume archive
- `config/appflowy_compose_dir.tgz` — AppFlowy compose/config directory if present
- `config/etc_zen-village.tgz` — Telegram/MCP env config
- `config/root_zen-village-secrets.tgz` — secret material
- `config/brain.zenvillagecr.com.nginx.conf` — public routing config
- `MANIFEST.txt`
- `SHA256SUMS`

Backups are stored under a `700` directory because they contain secrets.

## Verify Backup Integrity

```bash
ssh root@162.0.208.88 'cd /opt/zen-village/backups/appflowy/<timestamp> && sha256sum -c SHA256SUMS'
```

## Restore Strategy

Do not restore over production casually. A proper restore drill should use a temporary Postgres database/container first.

High-level production restore would be:

1. Stop AppFlowy services.
2. Restore Postgres from `postgres.dump`.
3. Restore MinIO volume from `minio_data.tgz`.
4. Restore relevant config/secrets if needed.
5. Start services.
6. Verify AppFlowy UI, MCP health, Telegram health, and database count.

Because restore is destructive to the live Brain, do not run it without explicit approval.

## First Backup

First backup was created on 2026-04-24 after acceptance checks passed.
