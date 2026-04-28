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
SERVICES/streasury-bot/scripts/deploy.sh
```

This runs the standard `infra/scripts/deploy-to-server.sh streasury-bot brain`
which handles:

1. Pre-deploy backup of `streasury` schema → `/opt/fpai/backups/streasury/`.
2. `rsync` source to `/opt/streasury-bot/` on Brain.
3. Build venv from pinned `requirements.txt` if needed.
4. Apply `schema/streasury_schema.sql` (idempotent — safe every deploy).
5. `systemctl daemon-reload && systemctl restart streasury-bot`.
6. Health: `curl http://127.0.0.1:8620/health` returns `{"ok": true, …}`.

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
