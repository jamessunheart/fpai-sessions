# /treasurer — Telegram command spec

**Member of:** AI Roster (Treasurer canonical: `TREASURER_CANONICAL.md`)
**Implementation target:** Loop 38
**Last updated:** 2026-05-09 (Loop 37 spec)

---

## Where it lives

- **Service:** `sh-brain-tgbot.service` on brain server `162.0.208.88`
- **Code:** `SERVICES/sunheart-brain/tgbot/handlers/treasurer.py` (new file)
- **Ports from:** `SERVICES/streasury-bot/app/handlers/cos.py` (deprecated `/money` handler — reuse parsing + formatting helpers)
- **Bot:** `@sunheartbrain_bot` (unified surface; not its own bot)

---

## Commands

| Command | Behavior |
|---|---|
| `/treasurer` | Current snapshot — liquid balance, MoM Δ, current burn, runway tiers |
| `/treasurer log income <amt> <src> [#project]` | Append income to ledger (project tag optional) |
| `/treasurer log expense <amt> <cat> [#project]` | Append expense to ledger (project tag optional) |
| `/treasurer digest` | Force weekly digest now |
| `/treasurer runway` | Show 30/60/90d projection at current burn |
| `/treasurer zv` | **Zen Village P&L view** — income, expenses, net by month |
| `/treasurer pnl <project>` | Per-project P&L (generalized from /treasurer zv) |
| `/treasurer help` | Command list |

---

## Project tags

Income and expense entries support optional `#project` tags so per-project P&L can be rendered. Suggested taxonomy (extend over time):

- `#zv` — Zen Village (labor, groceries, utilities, materials, retreat income)
- `#personal` — Miami, Chirripo, personal utilities
- `#infra` — servers, AI tools
- `#onebpo` — OneBPO income/expense
- `#camp-zen` — Founder/Creator Camp once it launches
- `#game` — Full Potential Game ops costs (separate from infra)

Untagged entries land in `#general` bucket. Treasurer's per-project view aggregates by tag.

---

## Data sources

1. **Primary local actuals:** `~/.config/fpai/treasury/treasurer_resources_<date>.md` (latest)
2. **Brain note canonical** (once MCP write recovers): `treasurer_resources_<date>` brain note
3. **Income ledger:** `~/.config/fpai/treasury/income_log.tsv` (TSV: date, amount, source, project, notes)
4. **Expense ledger:** `~/.config/fpai/treasury/expense_log.tsv` (TSV: date, amount, category, project, notes)
5. **fp-credits-gateway:** `/balance` API (master key in `/etc/fp-credits-gateway.env`)
6. **`/servers`:** Adam ROI ledger (Loop 22) for server-cost line

**Handler reads in priority order:** local file → brain note (if MCP up) → API endpoints.

---

## Output examples

### `/treasurer`

```
Treasurer · 2026-05-09

Liquid:    $152,916   (snapshot 2026-03-20, refresh pending)
Liab:      -$12,063
Net:       $140,854

Burn:      $8.4k+/mo  (known categories)
Income:    $15-30k/mo (avg, OneBPO → CN)
Net mo:    +$2 to +$22k typical

Runway @ max burn:  17 months (🟢 >12)
Pending inflow:     BEP $14k at +6mo

Reply: /treasurer zv | runway | digest
```

### `/treasurer zv`

```
Treasurer · Zen Village P&L · 2026-05

Income (this month):    $0
Income (YTD):           $0   ← no retreat revenue yet

Expenses (this month):
  Labor       $2,165
  Groceries     $650
  Utilities     $300
  Materials   ?? (manual log)
  Total      $3,115+

Net (this month):       -$3,115+
Net (YTD):              -$XX,XXX

Camp Zen Founder/Creator Camp launch will turn this positive.
```

### `/treasurer log expense 450 materials #zv`

```
✓ Logged: -$450 materials [#zv] on 2026-05-09
ZV month-to-date: -$3,565
```

---

## Voice rules (inherits from TREASURER_CANONICAL)

- Lead with numbers. Always.
- Deltas explicit (Δ +$X or Δ -$X)
- No "Great question!"; no commentary unless asked
- ⚠️ flags escalations only
- ≤12 lines per digest unless James asks for detail

---

## Auth

- Standard `@sunheartbrain_bot` Telegram auth (James's chat_id only — no other consumers in v1)
- Future: receivables stewards could query Norman/Adam via their own bots; that's a separate AI surface

---

## Effort

| Component | Time |
|---|---|
| Port `/money` handler to `treasurer.py` | 1.5h |
| Wire local-file reader for snapshot + ledgers | 30m |
| Add `/treasurer zv` and `/treasurer pnl` views | 45m |
| Income/expense log TSV writers | 30m |
| Weekly digest cron (Mon 09:00 CR) | 30m |
| Tests + first send to James | 30m |
| **Total** | **~4 hours** |

Fits Loop 38.

---

## Open spec questions

1. Should `/treasurer` also surface Camp Zen Founder/Creator Camp income separately when it launches, or fold into ZV P&L?
2. Should the bot ASK for missing materials/contractor cost monthly (push prompt) or wait for James to log?
3. Storage of ledgers: local file (TSV) v1, or brain notes v1, or both? (Local recommended for v1 — survives MCP outages.)
