# STreasury — Product Vision

> **What is it?** A Telegram-first finance/treasury tool for solo founders
> and small agencies. Backed by Actual Budget + SimpleFIN/GoCardless for
> bank sync, plus an AI council (Claude × OpenAI) that has memory across
> conversations and reads your real numbers — never guesses.

**Status:** Pre-product. Phase 1 (single-user, dogfooding) is shipped. Phase 2
(real bank data via Actual) is documented in PHASE2_ACTUAL.md. Phase 3
(productization) is sketched here.

---

## The wedge

| Audience | Problem | Why Telegram + AI wins |
|---|---|---|
| **Solo founders / indie hackers** | "Money flows from 9 places. I have no clean picture." | Lives where they live (Telegram). Ten seconds to log an expense vs. 2 minutes in QBO. |
| **Small agencies (3-15 people)** | "Bookkeeping is 80% data entry. Reports lag 2 months." | Photo a receipt, voice-note an expense, daily AI summary. |
| **Family offices / personal CFOs** | "Generic AI chatbots don't know our actual numbers." | Council has live access to the ledger. Memory across quarters. |
| **Crypto-native ops (DAOs, trading firms)** | "QBO doesn't speak Solana." | Multi-currency + on-chain RPC adapters. |
| **NOT v1**: regulated SMBs needing GAAP/IFRS, healthcare, anything needing audit signoff | Need certified tools (NetSuite, QBO). | Don't fight that battle yet. |

**v1 wedge: solo founders + 3-15 person agencies.** Underserved (QBO is bloated,
Wave is dying, Pennylane is EU-only), price-sensitive ($50-200/mo SaaS fits),
and they share the "get me out of dashboards" aesthetic.

---

## What's defensible

Every fintech tool has these layers. What's different about ours:

| Layer | Commodity tools have | We have |
|---|---|---|
| Bank/card sync | Plaid | **SimpleFIN + GoCardless** — fiat + crypto, no contract |
| Ledger | QBO/Xero proprietary | **Actual Budget (MIT)** — owners can self-host, leave anytime |
| UI | Web dashboards | **Telegram-first** — no learning curve |
| Reports | Static templates | **AI council** — synthesized weekly briefs, period-over-period |
| Ingest | Manual + bank sync | **Photo / voice / NL / CSV / PDF / on-chain / API** — every channel |
| Memory | None ("AI starts fresh") | **pgvector across briefs + transactions** — remembers Q2 decisions |

The combination is the moat. Each piece exists individually; nobody has glued
them together for SMBs in a Telegram-first form factor.

---

## Sequence (12 weeks)

| Week | Deliverable | Time |
|---|---|---|
| **Now** | `streasury-bot` works for me alone (FIRST_DEPLOY.md). Daily use. | ✅ Phase 1 shipped |
| **+1** | PHASE2_ACTUAL.md: Actual + SimpleFIN. My real numbers flow in. | 2 days |
| **+2** | Dogfood deeply. Note every UX rough edge. **Don't add features yet.** | — |
| **+3** | Recruit 2-3 friendly founders to use it. Charge them $0. Watch what they actually do. | 2 weeks setup + 2 weeks observation |
| **+6** | Per-tenant onboarding flow: Stripe Checkout → bot creation → SimpleFIN setup → first AI digest. Charge $19/mo. | 1 week |
| **+9** | If 2+ are using it weekly: scale to 10 paying customers via direct outreach. Don't market publicly yet. | 3 weeks |
| **+12** | Decide based on retention. Kill it, or commit to a real product roadmap. | — |

**The single most important constraint: dogfood for 4-6 weeks before showing it
to anyone external.** Every week not used for real numbers is a week guessing
what users want.

---

## Pricing intuition (calibration, not commitment)

Reference points:

| Tool | Price | Audience |
|---|---|---|
| Pennylane (FR/EU SMB) | €30-200/mo | French SMBs |
| Brex Empower | $0-50/mo + interchange | US startups |
| Numeral | $200-500/mo | Tax compliance |
| Maybe Finance (consumer) | $20/mo | Open-source consumer |
| Notion / Linear | $8-20/seat | "Tool I use daily" |

Sensible v1 plans:

| Tier | Price | Includes |
|---|---|---|
| **Solo** | $19/mo | 1 Telegram user, 1 Actual budget, 500 txn/mo, daily digest |
| **Team** | $79/mo | 5 users, multi-account, weekly council brief by email |
| **Pro** | $299/mo | Custom integrations, white-glove onboarding, API access |

Variable cost per active customer:

| Item | Cost |
|---|---|
| SimpleFIN | $1.25/mo (= $15/yr) |
| AI tokens (~50 daily messages, 4 council briefs/mo) | $2-5/mo |
| Postgres storage (1k txn/mo = 6 MB/yr) | <$0.10/mo |
| Telegram | $0 |
| **Total** | **~$4-6/mo** |
| **Solo plan margin** | **~70%** |

Healthy unit economics. Expensive things are **acquiring + supporting**
customers, not infra.

---

## What we never become

These are walls, not goals to push past.

⚠ **Never a money transmitter.** No initiating payments, no holding funds,
no transferring on behalf of users. Reporting/intelligence only. The moment
we touch payment flow, we're a regulated entity (state-by-state in the US,
EU under PSD2). Stay strictly read-only. If we ever need write capability,
partner with Stripe Treasury / Modern Treasury who hold the licenses.

⚠ **Never an auditor's tool.** We don't claim GAAP/IFRS compliance. We don't
generate tax forms. Customers needing audited books use QBO/Xero alongside us.
Our job is the daily heartbeat, not the year-end statement.

⚠ **Never a black box.** Customers can leave. Their data is in their own
Actual Budget instance + a clean Postgres schema we'll export on demand.
This is the open-source-tool insurance policy that makes founders trust it.

⚠ **Never auto-write without confirmation.** Every AI-parsed write asks
"Confirm?" by default. The setting that disables this exists for power-users
but is OFF for everyone by default. The AI never invents numbers — it reads
the snapshot, which only contains what the user (or a verified source) put
there.

---

## Beta tester invariants

These cannot regress while a beta tester has real money in the system:

1. **Never invent transactions.** API ambiguity = ask the user via Telegram, never write speculatively.
2. **Idempotent everything.** Re-running any sync = same ledger. Enforced by the unique index `(tenant_id, source, source_ref)`, not by adapter cleverness.
3. **No silent failures.** Sync errors set `last_sync_error` AND surface in tomorrow's digest ("Stripe failed yesterday").
4. **Read-only adapters.** Adapters MUST NOT initiate any payment, transfer, or external write. We're a reporting tool.
5. **Data export on demand.** A `/export` command (Phase 2) returns a SQLite snapshot of the user's tenant. They can leave anytime.
6. **AI provenance.** Every AI answer includes the model used. Council briefs include both raw answers + the synthesis. Auditable.
7. **Tenant isolation.** Every query filters by `tenant_id`. (Verified in Phase 1: every read in `app/ai/snapshot.py`, `app/reports/builders.py`, and `app/ledger.py` accepts and uses `tenant_id`.)
8. **Confirm-then-write by default.** `AUTO_CONFIRM=false` is the default. Power users can flip it; new users cannot accidentally have it on.

---

## What I'm not building yet

Resist the urge for any of these until paying customers ask twice:

- A web dashboard (Telegram is the UX).
- Mobile app (Telegram is the app).
- Billing UI (Stripe Checkout link is enough at <50 customers).
- Custom integrations beyond the listed adapters.
- White-label / on-premise licensing.
- A "team" multi-seat experience (just give them a shared bot for v1).

---

## What I am building first if products takes off

1. **Per-tenant bot tokens.** Today: one `@STreasury_Bot` with one owner. Productized: each tenant gets their own bot via Telegram Bot API (free), or a single shared bot with `/workspace` selector. **Decision: shared bot first** — simpler, no per-customer DevOps.
2. **Stripe Checkout onboarding.** New customer pays → webhook creates a tenant + sends them their bot link → they `/start` and we walk them through SimpleFIN setup conversationally.
3. **Audit log.** Append-only `streasury.audit_log` table with hash chain. Every write (manual, AI, sync) recorded with who/when/what.
4. **DPA + privacy policy.** Boilerplate suffices for v1 ($500 lawyer review). Real SOC2 only if/when we have the revenue to justify it (~$30k+/year process).
