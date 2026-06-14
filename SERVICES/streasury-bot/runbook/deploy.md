# Deploy runbook

## One-time

1. **Decide owner Telegram ID.** Message [@userinfobot](https://t.me/userinfobot)
   from your account, copy the numeric `Id`.
2. **(Recommended) Rotate the bot token** — the original token leaked into
   chat history. In Telegram → @BotFather → `/revoke` → pick `STreasury_Bot` →
   accept the new token. Save it; never paste it into chat again.
3. **Decide the database.** The default uses the same Postgres the brain
   already runs (`162.0.208.88:25432`, db `appflowy`). We isolate via a fresh
   `streasury` schema so we can never collide with brain tables.

   ```sql
   -- as a superuser on Brain:
   CREATE ROLE streasury LOGIN PASSWORD 'choose-something-strong';
   GRANT CONNECT ON DATABASE appflowy TO streasury;
   ALTER ROLE streasury IN DATABASE appflowy SET search_path = streasury, public;
   ```

   Then your `DATABASE_URL` is
   `postgres://streasury:choose-something-strong@127.0.0.1:25432/appflowy`.

## Deploy from the cockpit

```bash
SERVICES/streasury-bot/scripts/deploy.sh             # standard
SERVICES/streasury-bot/scripts/deploy.sh --dry-run   # show what would run
SERVICES/streasury-bot/scripts/deploy.sh --skip-backup  # first install only
```

The deploy script (which mirrors the existing per-service scripts in
`infra/scripts/`):

1. **Local syntax check** — every `app/*.py` must `py_compile` clean.
2. **Pre-deploy backup** to `/opt/fpai/backups/streasury-bot/<timestamp>/`
   plus a `pg_dump --schema=streasury` if the env file is configured.
3. `rsync` source to `/opt/streasury-bot/` on Brain.
4. Run `scripts/bootstrap.sh` remotely — creates user, venv, env-file
   skeleton (idempotent), applies schema, installs systemd unit.
5. `systemctl daemon-reload && systemctl restart streasury-bot`.
6. Health: `curl http://127.0.0.1:8620/health` returns `{"ok": true, …}`.

> **Note:** `AGENTS.md` references a canonical
> `infra/scripts/deploy-to-server.sh` that doesn't exist in this repo.
> Until that's added, `streasury-bot/scripts/deploy.sh` is the canonical
> path for this service and follows the same structure as the existing
> per-service scripts (`deploy-coracle-engine.sh`, `aria-safe-deploy.sh`).

## First-run on the server

After the first deploy, populate `/etc/streasury-bot/streasury.env` with
real values (token, owner id, AI keys, DB URL). Then:

```bash
systemctl restart streasury-bot
journalctl -u streasury-bot -f
```

Open Telegram, message [@STreasury_Bot](https://t.me/STreasury_Bot), send
`/whoami`. You should see your owner id echoed back. If you see nothing, the
bot is silently dropping messages because `OWNER_TG_ID` doesn't match.

## Smoke test

```text
/whoami
/accounts add stripe USD revenue
/log 4200 revenue stripe "April fp-credits"
/log -75 hosting primary "DO server"
/balance
/kpi set MRR 4200 USD
/report month
/ask why is hosting cost showing on the primary account?
/council should I shut down the legacy server next week?
```

## Rollback

```bash
SERVICES/streasury-bot/scripts/deploy.sh --rollback
# or:
systemctl stop streasury-bot
# restore from /opt/fpai/backups/streasury-bot/<timestamp>/
```
