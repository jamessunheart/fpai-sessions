# Command reference

## Logging money

| Command | Effect |
|---|---|
| `/log 4200 revenue stripe "April fp-credits"` | Insert a transaction. Positive = income, negative = expense. |
| `/expense 75 hosting primary "DO server"` | Same as `/log -75 …`. |
| `/income 600 consulting acme "April retainer"` | Same as `/log +600 …`. |
| _free text_ "spent 80 on gas" | AI parses → confirm-then-write. |
| _photo_ (receipt) | Vision model extracts → confirm-then-write. |
| _voice note_ "got 600 from acme" | Whisper → AI parse → confirm. |

The CSV importer is the only path that auto-imports without a per-row confirm —
it relies on the `(date, amount, vendor)` dedup hash to avoid double counting.

## Browsing

| Command | Effect |
|---|---|
| `/balance` | Per-account balances + USD total. |
| `/accounts list` | All accounts (incl. archived). |
| `/accounts add SLUG [CCY] [KIND]` | Create an account. KIND in {cash, crypto, revenue, obligation, virtual}. |
| `/accounts archive SLUG` / `/accounts unarchive SLUG` | Hide/show an account in `/balance`. |
| `/recent [N]` | Last N transactions (default 10, max 50). |
| `/holding btc 0.42` | Update a crypto holding (auto USD via CoinGecko). |

## Reports

| Command | Effect |
|---|---|
| `/report week` | Last 7 days. |
| `/report month` | MTD (current calendar month). |
| `/report ytd` | Year-to-date. |
| `/report 30d` / `/report 90d` | Rolling windows. |

## KPIs

| Command | Effect |
|---|---|
| `/kpi set MRR 4200 USD "April"` | Snapshot a metric. |
| `/kpi show MRR` | Sparkline + delta over last 30 points. |
| `/kpi list` | Latest value of every named KPI. |

## AI

| Command | Effect |
|---|---|
| `/ask <question>` | Single AI (default Claude). Faster, cheaper. |
| `/council <question>` | Claude + GPT in parallel + a chair-level synthesis. ~20-40s. |

Both calls receive a fresh treasury snapshot (accounts + holdings + last 90 days
of category aggregates + monthly trend + latest KPIs) so the AI grounds answers
on real numbers, not guesses.

## Importing

Send a CSV as a Telegram document. The parser auto-detects `date` and `amount`
columns (and optionally `description`/`vendor`/`category`). Each row gets a
`sha1(date|amount|vendor)` hash; re-importing the same statement is safe — only
new rows are inserted, dupes are skipped.

## Auth

The bot processes messages from `OWNER_TG_ID` only. Use `/whoami` to verify
your TG numeric id matches. Everyone else is silently ignored.
