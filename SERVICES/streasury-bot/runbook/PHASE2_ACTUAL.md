# Phase 2 — Actual Budget + SimpleFIN

> **Goal:** real bank/card data flowing into the bot's reports and AI council
> within 60 minutes of starting Phase 1 dogfooding.

**Pre-req:** Phase 1 deployed (`runbook/FIRST_DEPLOY.md` complete) and you've
used the bot for at least a few days with manual `/log` so you know what you
want from the AI.

---

## Step 1 — Sign up for SimpleFIN ($15/yr) (10 min)

1. Go to <https://bridge.simplefin.org>.
2. Click "Subscribe" → pay $15 for 1 year (Stripe checkout).
3. Click "+ Add Account" → search your bank (Chase, BoA, Mercury, Wise, etc.).
4. Authenticate with your bank credentials. SimpleFIN brokers a read-only
   connection — they never see your password after the OAuth-like flow.
5. Repeat for every account/card you want tracked.
6. Once accounts are connected, click "Generate Setup Token". You get a
   long string starting `https://beta-bridge.simplefin.org/simplefin/claim/...`.
   **Copy this. It's the only thing you need.**

> SimpleFIN's setup token is one-time-use. The first system to claim it gets
> a permanent `access_url`. We claim it from Actual in step 3.

---

## Step 2 — Run Actual Budget on Brain (15 min)

```bash
ssh root@162.0.208.88

mkdir -p /opt/actual && cd /opt/actual
cat > docker-compose.yml <<'YAML'
services:
  actual:
    image: actualbudget/actual-server:latest
    container_name: actual
    restart: unless-stopped
    ports:
      - "5006:5006"
    volumes:
      - ./data:/data
    environment:
      - ACTUAL_TRUSTED_PROXIES=127.0.0.1,::1
YAML

docker compose up -d
docker logs -f actual  # ctrl-C once you see "Listening on 0.0.0.0:5006"
```

Open `http://162.0.208.88:5006` in your browser. Set a server password
(remember it). Create a new budget called "Treasury".

> ⚠ **Don't expose port 5006 publicly yet.** SSH-tunnel to it for now:
> `ssh -L 5006:localhost:5006 root@162.0.208.88` then visit `localhost:5006`.
> When you want it on a real domain (`actual.sunheart.com`), add an nginx
> vhost behind basic auth. For Phase 2, tunneling is fine.

### Connect SimpleFIN to Actual

In Actual:
1. Open the budget → settings (gear icon, top-left) → "Show advanced settings".
2. Click "Edit" next to "SimpleFIN".
3. Paste your **setup token** from step 1. Click "Continue".
4. Actual claims it and stores the permanent `access_url`. The token
   self-destructs after this exchange.
5. Back to budget view → click "Add account" → "I'll set this up myself" → no,
   actually: "Setup from SimpleFIN" → choose each account, click "Save".
6. Actual now imports the last 90 days of every account.

---

## Step 3 — Generate Actual API token (5 min)

In Actual: settings → "Show advanced settings" → "Server URL" — note the URL
(should be `http://localhost:5006`). Then settings → "Reset password / generate
new" — copy the API token (or set the password, whichever Actual prompts).

We'll store this in `/etc/streasury-bot/streasury.env`:

```bash
ACTUAL_SERVER_URL=http://localhost:5006
ACTUAL_PASSWORD=<server password from earlier>
ACTUAL_BUDGET_ID=<get this from Actual UI: settings > "Show advanced" > "Sync ID">
```

---

## Step 4 — Implement the Actual adapter (30 min)

The current `app/sources/actual.py` is a stub. Replace it with a real
implementation that:

1. Spawns a small Node helper that uses `@actual-app/api` (the only sanctioned
   client, no Python SDK exists). The helper:

   ```js
   // SERVICES/streasury-bot/app/sources/actual_helper.js
   const api = require('@actual-app/api');

   (async () => {
     await api.init({
       dataDir: '/tmp/actual-streasury',
       serverURL: process.env.ACTUAL_SERVER_URL,
       password: process.env.ACTUAL_PASSWORD,
     });
     await api.downloadBudget(process.env.ACTUAL_BUDGET_ID);

     const since = process.argv[2] || '2025-01-01';
     const accounts = await api.getAccounts();
     for (const acc of accounts) {
       const txns = await api.getTransactions(acc.id, since);
       for (const t of txns) {
         process.stdout.write(JSON.stringify({account: acc, txn: t}) + '\n');
       }
     }
     await api.shutdown();
   })();
   ```

2. The Python adapter shells out, parses each JSON line, and calls
   `ledger.insert_txn(source="actual", source_ref=t.id, ...)` for each.

3. Stores `since` in `streasury.source_connection.config` so subsequent syncs
   are incremental.

Install Node deps once:

```bash
ssh root@162.0.208.88
cd /opt/streasury-bot/app/sources
npm init -y
npm install @actual-app/api
```

Add `node` to the streasury user's PATH or shell out to
`/usr/bin/node /opt/streasury-bot/app/sources/actual_helper.js ...`.

---

## Step 5 — Register the connection in the DB (1 min)

```sql
INSERT INTO streasury.source_connection (tenant_id, kind, label, secret, config)
VALUES (
    1,
    'actual',
    'Personal Treasury (via Actual)',
    'unused-actual-uses-env-vars',
    '{"since": "2025-01-01"}'
);
```

---

## Step 6 — Run first sync (1 min)

For now, on the server:

```bash
sudo -u streasury /opt/streasury-bot/.venv/bin/python -c "
import asyncio
from app.sources import base, actual
asyncio.run(base.run_all())
"
```

Expected: `{"Personal Treasury (via Actual)": SyncResult(seen=N, inserted=N, ...)}`
where N is the count of transactions Actual has for the last 90 days.

Once this works, add a daily systemd timer so it runs at 06:00 UTC:

```ini
# /etc/systemd/system/streasury-bot-sync.service
[Unit]
Description=streasury-bot daily source sync

[Service]
Type=oneshot
User=streasury
EnvironmentFile=/etc/streasury-bot/streasury.env
WorkingDirectory=/opt/streasury-bot
ExecStart=/opt/streasury-bot/.venv/bin/python -m app.sources.runner
```

```ini
# /etc/systemd/system/streasury-bot-sync.timer
[Unit]
Description=streasury-bot daily sync

[Timer]
OnCalendar=*-*-* 06:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl enable --now streasury-bot-sync.timer
```

(`app/sources/runner.py` is a 5-line module that calls `base.run_all` and
sends a Telegram summary — to write in Phase 2.)

---

## Step 7 — Verify on Telegram (2 min)

```
/balance
```

Should now show all your real accounts (Chase, Mercury, Wise, etc.) with
real balances pulled from Actual which got them from SimpleFIN which got
them from your banks.

```
/report month
```

Should show real income/expense by category for the current month.

```
/ask what's our cash runway at current burn?
```

The AI now has real numbers to reason on.

---

## Phase 2.5 — Add Stripe (30 min, when revenue starts flowing)

Stripe is its own adapter, simpler than Actual:

1. Create a restricted API key in Stripe dashboard (read-only on
   Charges + Balance Transactions).
2. Insert into `source_connection`:
   ```sql
   INSERT INTO streasury.source_connection (tenant_id, kind, label, secret, config)
   VALUES (1, 'stripe', 'Stripe Live', 'rk_live_...', '{"since": "2025-01-01"}');
   ```
3. Implement `app/sources/stripe.py` — see the stub for the plan, ~80 LOC.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Actual UI says "could not connect to SimpleFIN" | Token already claimed (one-time-use). Generate a new setup token from SimpleFIN. |
| Actual imports show wrong amounts | SimpleFIN sometimes flips signs. Toggle "Inverted" in Actual's account settings. |
| Adapter inserts duplicates | The unique index `(tenant_id, source, source_ref)` should prevent this. If it doesn't, your `source_ref` isn't stable — use Actual's transaction `id` (a UUID), never an index or timestamp. |
| Adapter hangs | Node helper blocked. `pkill -f actual_helper.js` and check `journalctl -u streasury-bot`. |
| Sync says 0 inserted but UI shows new txns in Actual | `config.since` is set too late. Update it: `UPDATE streasury.source_connection SET config = '{"since": "2025-01-01"}' WHERE label = 'Personal Treasury (via Actual)';` |

---

## What to NOT do in Phase 2

- ❌ Don't expose Actual to the public internet without auth. SimpleFIN
  access_urls live in Actual's data dir; if exposed, attackers can read your
  bank data.
- ❌ Don't disable the bot's confirm-then-write step. Even on synced data,
  category re-mapping should pass through human review.
- ❌ Don't add Plaid yet. SimpleFIN handles your banks. Plaid's contract
  overhead isn't worth it until a customer's bank isn't supported.
- ❌ Don't try to write back to Actual yet. Phase 1 logs go into our schema
  only. Bidirectional sync (Telegram log → Actual) is Phase 3 — needs
  careful conflict resolution.
