# Brain Index Recovery Playbook

This recovers `brain_index` if server `162` is gone. Target recovery time from a bare Ubuntu server: under 2 hours once DNS/SSH access and the latest backup are available.

## 1. Provision Replacement Server

Minimum: Ubuntu 22.04 or 24.04, 2 vCPU, 4 GB RAM, 40 GB SSD. Prefer 4 vCPU, 8 GB RAM, 80 GB SSD if available.

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-client gzip git rsync python3-venv
sudo systemctl enable --now postgresql
```

Create the database and user. Use the same credentials recorded in the secret store or `/etc/sh-brain/curator.env` backup.

```bash
sudo -u postgres createuser --pwprompt sh_brain
sudo -u postgres createdb -O sh_brain brain_index
```

## 2. Restore Latest Backup

Copy the newest offsite backup to the new host. Example:

```bash
mkdir -p /opt/fpai-backup
scp backup-host:/path/to/fpai-backups/brain_YYYY-MM-DD_HH-MM.sql.gz /opt/fpai-backup/
chmod 600 /opt/fpai-backup/brain_YYYY-MM-DD_HH-MM.sql.gz
```

Restore into the empty database:

```bash
export PGPASSWORD='<password from curator.env>'
gunzip -c /opt/fpai-backup/brain_YYYY-MM-DD_HH-MM.sql.gz \
  | pg_restore --clean --if-exists --no-owner --dbname=postgresql://sh_brain@localhost/brain_index
```

Verify the archive before restore if needed:

```bash
gzip -t /opt/fpai-backup/brain_YYYY-MM-DD_HH-MM.sql.gz
gunzip -c /opt/fpai-backup/brain_YYYY-MM-DD_HH-MM.sql.gz | pg_restore --list >/tmp/brain_restore.list
```

## 3. Restore Flat-File Memory From Git

```bash
mkdir -p /opt/fpai-build
cd /opt/fpai-build
git clone <repo-url> FPAI_Cockpit
cd FPAI_Cockpit
git checkout feat/headless-build
```

If a deploy mirror exists, restore `/opt/sh-brain-src` from the repo/service deployment path used by the current `sh-brain-*` services.

## 4. Recreate Runtime Env

Recreate `/etc/sh-brain/curator.env` with the restored Postgres credentials and bot credentials. Minimum expected DB values:

```bash
DATABASE_URL=postgresql://sh_brain:<password>@localhost/brain_index
PGHOST=localhost
PGDATABASE=brain_index
PGUSER=sh_brain
PGPASSWORD=<password>
```

Do not commit this file. Keep mode restricted:

```bash
sudo chown root:root /etc/sh-brain/curator.env
sudo chmod 600 /etc/sh-brain/curator.env
```

## 5. Restart Services In Order

Install or copy systemd units, then restart the database-facing services first:

```bash
sudo systemctl daemon-reload
sudo systemctl restart postgresql
sudo systemctl restart sh-brain-index.service
sudo systemctl restart sh-mcp-http.service
sudo systemctl restart sh-brain-tgbot.service
sudo systemctl restart fpai-build-loop.timer fpai-council.timer fpai-morning-digest.timer
sudo systemctl enable --now fpai-brain-backup.timer fpai-brain-backup-verify.timer
```

## 6. Verify Brain Tables And Row Counts

```bash
export PGPASSWORD='<password from curator.env>'
psql -h localhost -U sh_brain -d brain_index -c '\dt brain_index.*'
psql -h localhost -U sh_brain -d brain_index -c "
SELECT 'decisions' AS table, COUNT(*) FROM brain_index.decisions
UNION ALL SELECT 'corrections', COUNT(*) FROM brain_index.corrections
UNION ALL SELECT 'thread', COUNT(*) FROM brain_index.thread
UNION ALL SELECT 'tg_messages', COUNT(*) FROM brain_index.tg_messages;
"
```

All tables should exist. Counts should be non-zero for the tables that had live data on `162`.

## 7. Re-Run Health Check

```bash
cd /opt/fpai-build/FPAI_Cockpit
bash tools/build_loop/health_check.sh
bash tools/infra/verify_backup.sh
```

Expected result: health check completes without a backup freshness failure, and backup verification logs `backup_verified` with `valid=true`.
