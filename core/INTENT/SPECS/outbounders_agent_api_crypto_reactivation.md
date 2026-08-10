# Spec — Outbounders Agent API · Crypto Rails · Safe Reactivation

**Status:** Approved direction (James 2026-08-10: "build infrastructure so other AI systems can easily api in, use crypto to purchase the talent pool or post jobs, re-activate safely").
**Author:** Ember
**Context:** New site live 2026-08-10 ("Hire AI-augmented remote agents · $25 to start"). Script generator live at /ai. This spec is the P2+ arc: make Outbounders the talent layer other AI systems can programmatically buy.

## Live pool (measured 2026-08-10, production DB)

| Segment (by last login) | Agents | Clients |
|---|---:|---:|
| Hot (≤90d) | 527 | 347 |
| Warm (90d–1yr) | 2,162 | 379 |
| Cool (1–3yr) | 26,104 | 479 |
| Cold (3yr+) | 64,579 | 17,926 |
| Email-verified (all) | 25,055 | 9,475 |
| Verified AND active ≤3yr | 1,713 | 403 |

**Honest frame:** the immediately-usable pool is ~2,700 warm agents (hot+warm), with ~26K cool as the reactivation frontier. The "94K agents" is a story number, not an ops number.

## Phase A — Agent API v0 (build first; no money movement, lowest risk)

Sidecar service on 209.74.93.72 (Python FastAPI or PHP, own port + subdomain `api.outbounders.com`), reads existing `obapp_outbounders` DB. Never blocks the legacy app.

Endpoints (v0):
- `GET /v1/talent` — search agents: skills, country, hourly rate, availability, AI-tools-trained flag. **Anonymized** (no emails/names until hire — anti-scrape).
- `POST /v1/jobs` — post a job (maps to `client_job_posting`).
- `GET /v1/jobs/{id}/applications` — poll applications.
- `POST /v1/webhooks` — register callbacks (new application, hire accepted, hours logged).
- Auth: `api_keys` table (new), bearer keys, per-key rate limits + scopes. Keys issued via client dashboard (existing accounts only, v0).

**AI-native layer:** MCP server wrapping the same endpoints (`outbounders-mcp`), so Claude/GPT agents can hire directly. This is the differentiator — first outbound-talent marketplace with an MCP surface.

## Phase B — Crypto rails (James-gated: money = RESERVED class)

- v0: **USDC via hosted processor** (Coinbase Commerce or equivalent) → credits existing ledger (`main_transaction`) as deposits. No custody, no new wallet infra, minimal license surface.
- API: `POST /v1/deposits/crypto` returns a payment link/address; webhook confirms → ledger credit.
- Later: agent payouts in stablecoin (PH remittance saves agents 3-7% vs current rails) — separate spec + compliance pass before build.
- **Gate:** James signs off on processor account + terms before anything goes live.

## Phase C — Safe reactivation (sequenced AFTER A gives them something to return to)

Deliverability discipline (the "don't get blocked" plan):
1. **Preflight:** verify SPF/DKIM/DMARC on outbounders.com; send from a dedicated subdomain (`mail.outbounders.com`) so the root domain's reputation is insulated.
2. **Ladder:** hot 527 → warm 2,162 → verified-cool only (email_verified AND active ≤3yr) → stop. Cold 64K stays untouched in v1 (bounce-bomb risk).
3. **Throttle:** start 100-200/day, double weekly only if bounce <2% AND complaint <0.1%; hard-stop automation on breach.
4. **Hygiene:** pre-send validation pass (syntax + MX + known-disposable) on cool segment; suppression list honored forever; one-click unsubscribe (List-Unsubscribe header — Gmail requirement).
5. **Message:** agents get "learn to work with AI — free training, new AI-augmented jobs" (the pivot story), clients get "the platform is AI-augmented now + API access." No "we fixed our site" energy.
6. **Re-permission:** cool segment gets a single re-opt-in email; only confirmed clicks enter the regular stream.
7. **Gate:** James approves template + first batch before any send (outward-facing).

## Sequence & effort

| Step | What | Effort |
|---|---|---|
| A1 | `api_keys` table + FastAPI sidecar + talent/jobs endpoints | 2-4 days AI-build |
| A2 | MCP server wrapper + docs page (`/developers`) | 1-2 days |
| B1 | USDC deposits via processor (James opens account) | 2-3 days after gate |
| C1 | Deliverability preflight + hot-segment send | 1 day + James template approval |
| C2 | Ladder execution, engagement-gated | weeks, automated |

Success metrics: API keys issued · jobs posted via API · first crypto deposit · reactivated logins (target: 10% of hot, 5% of warm) · zero blacklist events.

Related: [[project-outbounders-ai-outsourcing-pivot]] · [[project-outbounders-scriptgen-live]] · `core/STATE/OUTBOUNDERS_REVENUE_AUDIT.md`.
