# First deploy — one-shot bring-up

> **Goal:** from "scaffold committed" → "I can text @STreasury_Bot and it logs
> a transaction" in ~20 minutes.

There are five things to do, in this order. Each one is independent of the
others; the bot won't *work* until all five are done, but you can do them in
any order and pause anywhere.

---

## 1. Rotate the bot token (2 min) ⚠ Required

The original token leaked into chat history. Rotate it now.

1. Open Telegram → message [@BotFather](https://t.me/BotFather).
2. Send `/revoke` → choose `STreasury_Bot` → confirm.
3. Copy the new token. **Don't paste it back into chat.** You'll save it to a
   file in step 4.

---

## 2. Find your Telegram user ID (1 min) ⚠ Required

The bot ignores everyone but you.

1. Message [@userinfobot](https://t.me/userinfobot).
2. Copy the numeric `Id` (e.g. `123456789`). This is your `OWNER_TG_ID`.

---

## 3. Create the database role (3 min) ⚠ Required

We isolate via a dedicated `streasury` schema in the existing brain Postgres.

```bash
ssh root@162.0.208.88
sudo -u postgres psql -d appflowy <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'streasury') THEN
        CREATE ROLE streasury LOGIN PASSWORD 'CHOOSE_A_STRONG_PASSWORD';
    END IF;
END$$;
GRANT CONNECT ON DATABASE appflowy TO streasury;
ALTER ROLE streasury IN DATABASE appflowy SET search_path = streasury, public;
CREATE SCHEMA IF NOT EXISTS streasury AUTHORIZATION streasury;
SQL
exit
```

Replace `CHOOSE_A_STRONG_PASSWORD` with a real one (24+ random chars). Save it.

Your `DATABASE_URL` is now:

```
postgres://streasury:CHOSEN_PASSWORD@127.0.0.1:25432/appflowy
```

> **Note on port:** the brain Postgres listens on `25432` (mapped from the
> Docker container). If your setup differs, run
> `ssh root@162.0.208.88 'docker ps | grep postgres'` and use the host port
> shown.

---

## 4. Deploy (5 min) — runs the bot, but it'll idle until step 5

From your Mac:

```bash
cd /Users/jamessunheart/FPAI_Cockpit
SERVICES/streasury-bot/scripts/deploy.sh --skip-backup
```

`--skip-backup` is fine on the *first* deploy because there's nothing to back
up yet. Subsequent deploys: drop the flag.

The script will:
- Sync `SERVICES/streasury-bot/` → `/opt/streasury-bot/` on Brain.
- Run `bootstrap.sh` remotely (creates `streasury` user, venv, systemd unit,
  installs deps, applies schema).
- Start the systemd unit.
- Show the health check (will be `{"ok": false}` because env not yet
  populated — that's expected, fix in step 5).

---

## 5. Populate the env file (3 min) ⚠ Required

```bash
ssh root@162.0.208.88
nano /etc/streasury-bot/streasury.env
```

Set these (everything else has sensible defaults):

```bash
TELEGRAM_BOT_TOKEN=<paste new token from step 1>
OWNER_TG_ID=<your number from step 2>
ANTHROPIC_API_KEY=<your existing Anthropic key>
OPENAI_API_KEY=<your existing OpenAI key>
DATABASE_URL=postgres://streasury:CHOSEN_PASSWORD@127.0.0.1:25432/appflowy
```

Then:

```bash
chmod 0640 /etc/streasury-bot/streasury.env
chown root:streasury /etc/streasury-bot/streasury.env
systemctl restart streasury-bot
journalctl -u streasury-bot -n 30 --no-pager
```

You should see:

```
streasury-bot starting; owner=<your-id>
streasury.db db pool ready
INFO: Uvicorn running on http://0.0.0.0:8620
```

If you see a Postgres connection error, the password or host in `DATABASE_URL`
is wrong. Tail with `journalctl -u streasury-bot -f` while you fix it.

---

## 6. Smoke test (2 min)

In Telegram, message [@STreasury_Bot](https://t.me/STreasury_Bot):

```
/whoami
```

Expected reply: `You are <your id>. Owner: <your id>` — they should match.

If you see no reply: the bot is silently dropping you (`OWNER_TG_ID` mismatch).
Check `journalctl -u streasury-bot -f` for `ignoring non-owner user <id>`.

Then run the real test:

```
/accounts add stripe USD revenue
/accounts add operating USD cash
/log 4200 revenue stripe "April fp-credits test"
/log -75 hosting operating "DO server"
/balance
/kpi set MRR 4200 USD
/report month
/ask why is hosting on the operating account?
/council should I shut down the legacy server next week?
```

If `/balance` shows the two accounts and `/ask` returns a Claude response that
references your $4,200 in revenue, the bot is fully wired up. 🎉

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| No reply at all in Telegram | `OWNER_TG_ID` mismatch. `journalctl -u streasury-bot -f` will show the user id it's seeing. |
| `psycopg.errors.InvalidPassword` | Fix the password in `DATABASE_URL`. |
| `psycopg.errors.OperationalError: connection refused` | Wrong port. `docker ps \| grep postgres` on Brain to find the real host port. |
| `/health` returns `{"ok": false}` with auth error | Env file not loaded. Confirm `EnvironmentFile=/etc/streasury-bot/streasury.env` matches reality. `systemctl cat streasury-bot`. |
| AI commands fail with `401` | Wrong Anthropic / OpenAI key. |
| `/import` says "Couldn't detect date/amount" | The CSV header doesn't have a column matching `date` or `amount`. Add a header row or rename columns. |
| Receipt photo gives "couldn't read a transaction" | OpenAI vision didn't recognize it. Try a clearer photo or just type the transaction. |

---

## Phase 2 hooks (next session)

Once the bot is in daily use, the next moves (in order of leverage):

1. **Stand up Actual Budget on Brain** (Docker, port 5006). Connect SimpleFIN.
2. **Refactor `app/ledger.py`** to write through the Actual API, keep our
   schema only for KPIs / conversations / council briefs.
3. **Add `app/sources/`** — daily cron pull adapters for Stripe, DigitalOcean,
   ZEND payments, WhaleTrack.
4. **Brain (pgvector) integration** — index council briefs and AI conversations
   so `/ask` has memory across sessions.
