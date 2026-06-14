# STreasury Bot — Sovereign Treasury for Telegram

> **One conversation, every number.** Telegram bot at [@STreasury_Bot](https://t.me/STreasury_Bot)
> backed by Postgres + Anthropic + OpenAI. Log money via chat, photo, or voice.
> Ask the AI council why something moved. Run reports across cash, crypto,
> trading, revenue, and any custom KPI you want to track.

**Status:** Phase 1 scaffold (logging + reports + council). Receipt OCR, PDF
statements, and adapter pulls (Stripe / DigitalOcean / WhaleTrack / ZEND) land
in Phase 2.

**Host:** Brain server `162.0.208.88`, port `8620`, systemd unit
`streasury-bot.service`.

**Database:** schema `streasury` inside the brain Postgres (port `25432`).

---

## What it does

| You send | Bot does |
|---|---|
| `/log 1200 revenue zenvillage "guest #3 deposit"` | Inserts a transaction; replies with new balance for the account. |
| `/expense 75 hosting "primary server"` | Shorthand for `/log -75 …`. |
| `/income 4200 stripe "April fp-credits"` | Shorthand for `/log +4200 …`. |
| `/balance` | Per-account balances + total cash position. |
| `/accounts add stripe USD` | Create or archive accounts. |
| `/holding btc 0.42` | Updates a crypto holding (auto USD via CoinGecko). |
| `/kpi set MRR 4200` | Snapshot a named metric. |
| `/kpi show MRR` | Sparkline + trend (last 30 days). |
| `/report week` / `month` / `ytd` | Markdown P&L + KPI deltas + variance. |
| `/ask why is hosting up 30%?` | Single AI (cheaper) with live treasury snapshot context. |
| `/council should I kill the legacy server?` | Claude + OpenAI in parallel + synthesis paragraph. |
| `/import` (then upload a CSV) | Schema-detects, previews, batch inserts. Dedup by `(date, amount, vendor)` hash. |
| Photo of a receipt | Vision model extracts vendor/date/amount/category → confirm-then-write. |
| Voice note ("spent 80 on gas") | Whisper transcribes → NL parser → confirm-then-write. |
| Free text ("got 600 from client X") | AI parses intent → confirm-then-write. |
| `/help` | Full command reference. |

All non-owner messages are silently ignored (whitelisted by Telegram user ID).

---

## Architecture

```
                  ┌────────────────────────────┐
                  │        Telegram (you)       │
                  └─────────────┬──────────────┘
                                │ messages, photos, PDFs, voice
                                ▼
                  ┌────────────────────────────┐
                  │   streasury-bot            │
                  │   long-poll worker (Python)│
                  │   + FastAPI (reports/web)  │
                  └─────────────┬──────────────┘
                                │
        ┌───────────────────────┼─────────────────────┐
        ▼                       ▼                     ▼
   ┌─────────┐           ┌──────────────┐      ┌──────────────┐
   │Postgres │           │ AI Council    │      │ Adapters     │
   │streasury│           │ Claude +      │      │ stripe / DO  │
   │ schema  │           │ OpenAI +      │      │ whaletrack / │
   │         │           │ vision +      │      │ zend / SOL   │
   │ledger,  │◀────cron──│ Whisper       │      │ (Phase 2)    │
   │kpis,    │           └──────────────┘      └──────────────┘
   │imports  │
   └─────────┘
```

Source adapters (Phase 2) sync into the same `streasury.transaction` table
with `source='stripe'` etc. — so reports and AI questions hit one schema, not
seven flaky APIs at query time.

---

## Directory layout

```
SERVICES/streasury-bot/
├── README.md                  # this file
├── pyproject.toml             # python-telegram-bot v21, fastapi, sqlalchemy, asyncpg, anthropic, openai
├── requirements.txt           # pinned for systemd venv
├── .env.example               # all secrets named, none filled
├── app/
│   ├── __init__.py
│   ├── __main__.py            # python -m app  → starts bot
│   ├── config.py              # pydantic-settings loader for .env
│   ├── db.py                  # async psycopg pool (mirrors curator/db.py)
│   ├── telegram.py            # send / edit / answer_callback / file_download
│   ├── tgbot.py               # main long-poll loop + owner whitelist
│   ├── ai/
│   │   ├── llm.py             # generic completion (Claude or OpenAI)
│   │   ├── council.py         # parallel both + synthesis
│   │   ├── snapshot.py        # builds "current treasury state" context for AI
│   │   ├── parse.py           # NL "spent 80 on gas" → structured intent
│   │   ├── vision.py          # receipt photo → vendor/date/amount/category
│   │   └── voice.py           # Whisper transcription
│   ├── handlers/
│   │   ├── log.py             # /log /expense /income + free-text + voice + photo
│   │   ├── balance.py         # /balance /accounts
│   │   ├── holding.py         # /holding (crypto + valuation)
│   │   ├── kpi.py             # /kpi set / show / list
│   │   ├── report.py          # /report week|month|ytd|custom
│   │   ├── ask.py             # /ask /council
│   │   └── import_.py         # /import → CSV upload flow
│   └── reports/
│       ├── builders.py        # SQL aggregations
│       └── formatters.py      # markdown tables for Telegram
├── schema/
│   └── streasury_schema.sql   # idempotent CREATE SCHEMA + tables + indexes
├── scripts/
│   ├── bootstrap.sh           # apply schema, install systemd, start service
│   ├── deploy.sh              # uses infra/scripts/deploy-to-server.sh
│   └── psql.sh                # quick shell into the schema
├── systemd/
│   └── streasury-bot.service
└── runbook/
    ├── deploy.md
    ├── commands.md            # full /command reference
    ├── backup.md
    └── revoke-token.md        # how to rotate the bot token via @BotFather
```

---

## Quick start (local dev)

Fastest beta bring-up (prompts + deploy + env + restart):

```bash
cd /Users/jamessunheart/FPAI_Cockpit
SERVICES/streasury-bot/scripts/quickstart.sh
```

Manual/local dev flow:

```bash
cd SERVICES/streasury-bot
cp .env.example .env
# Fill TELEGRAM_BOT_TOKEN, OWNER_TG_ID, ANTHROPIC_API_KEY, OPENAI_API_KEY,
# DATABASE_URL (postgres://user:pass@host:port/db).

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Apply schema (idempotent):
psql "$DATABASE_URL" -f schema/streasury_schema.sql

# Run the bot:
python -m app
```

Open Telegram, message [@STreasury_Bot](https://t.me/STreasury_Bot), send `/help`.
First message from the owner ID auto-binds; messages from anyone else are
silently dropped.

---

## Deploy (Brain server)

Per `AGENTS.md`: never SSH directly. Always:

```bash
SERVICES/streasury-bot/scripts/deploy.sh
# → calls infra/scripts/deploy-to-server.sh streasury-bot brain
```

The deploy script:

1. Pre-deploy backup (snapshot `streasury` schema → `/opt/fpai/backups/streasury/`).
2. `rsync` source to `/opt/streasury-bot/` on Brain.
3. Build venv from pinned `requirements.txt`.
4. Apply `schema/streasury_schema.sql` (idempotent — safe on every deploy).
5. `systemctl daemon-reload && systemctl restart streasury-bot`.
6. Health check: `curl http://127.0.0.1:8620/health` returns 200 within 30s.

---

## Security

- Bot token + API keys live in `/etc/streasury-bot/streasury.env` (root:streasury, mode 0640) on the server. Never in git, never in chat.
- `OWNER_TG_ID` is the only Telegram user whose messages are processed; everyone else is silently dropped.
- All AI writes require explicit `Yes / Edit / Cancel` confirmation by default. Toggle `AUTO_CONFIRM=true` only for trivial intents (e.g. confirmed CSV imports).
- Webhook mode is **not used** — long-polling avoids opening any inbound port for the Telegram API.
- Token in this conversation is treated as compromised. See `runbook/revoke-token.md` for rotation via `@BotFather → /revoke`.

---

## Phase 2 (next)

- PDF statement parser (`pdfplumber` + AI column normalizer).
- Stripe adapter — daily sync of charges/payouts/fees → `transactions`.
- DigitalOcean adapter — billing API → recurring `obligations`.
- WhaleTrack adapter — trading P&L into `transactions` with `source='whaletrack'`.
- ZEND payments adapter — internal credit settlements.
- Solana wallet watcher (read-only) — on-chain balances + tx history.
- Anthropic + OpenAI billing API — actual AI spend tracking.

## Phase 3 (when needed)

- Email-forward intake (`receipts@…` IMAP poller).
- Brain (pgvector) integration so AI remembers prior reports + decisions.
- Web dashboard (FastAPI + simple HTML) at `streasury.sunheart.com`.
