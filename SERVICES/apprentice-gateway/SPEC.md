# SPEC — Apprentice Gateway (v0.2 · adds Character tier)

**Version:** 0.2.0 (Phase 1 + Character extension · 2026-05-19)
**Port:** 8772 (reserved · not yet bound)
**Status:** Code complete · NOT deployed · NOT live · awaiting James Y/N

## v0.2 additions (Character tier)

The gateway now hosts **two** monetization tiers on the same service:

- **Apprentice** ($97/mo + $497 founding one-time · cap 30) — original Phase 1 product
- **Character** ($2,497/mo + $4,997 co-design one-time · cap 7 founding) — application-gated founding cohort

Both tiers share:
- The same FastAPI app + port 8772
- The same SQLite database (separate `apprentices` and `characters` tables)
- The same Stripe account + webhook endpoint (branched on `metadata.tier`)
- The same admin token

Character-specific routes:
- `GET /character/` → landing page
- `GET /character/seats` → live founding-7 counter
- `POST /character/apply` → application submission (no payment yet)
- `POST /character/checkout` → ADMIN-only Stripe checkout link generation (after James reviews application)
- `GET /character/status/{email}` → membership state
- `GET /character/welcome` → post-checkout welcome page

Character admin routes:
- `GET /admin/character/applications` → list applications (filter by status)
- `POST /admin/character/applications/{id}/accept` → mark accepted
- `POST /admin/character/applications/{id}/decline` → mark declined
- `GET /admin/characters` → list active Characters
- `POST /admin/character/replay-provisioning/{email}` → re-run provisioning chain

Character provisioning chain (`app/character_provisioning.py`) — 5 steps, each feature-flagged:
1. `brain_account` — full-tier brain-server user
2. `identity_stack` — 10-file identity template populated to their vision
3. `tg_invite` — `@characters` founder-circle channel
4. `welcome_packet` — Haiku-drafted personalized welcome email with 1:1 booking link
5. `narrator_bootstrap` — register Character as Narrator agent subject

Full provisioning sequence documented at `~/.config/fpai/character_launch/PROVISIONING_SEQUENCE.md`.

## Original v0.1 spec follows

## Purpose

The Champion Stack Apprentice payment + provisioning service. Handles Stripe checkout for the $97/mo subscription and optional $497 founding tier, and on successful payment auto-provisions the apprentice across the substrate (Champion card update, brain-server account, TG invite, welcome email).

## Position in ecosystem

- **Upstream:** Landing page at `https://fullpotential.com/apprentice` (and the Stripe checkout it triggers)
- **Downstream:** champion-sign (port 8770) · sunheart-brain (port 8000) · TG bot (`@sunheartbrain_bot`) · mail pipeline
- **NOT the same as:** fp-credits-gateway (port 8765) — that is the internal credits ledger (FPC / CC / USD bookkeeping). This new service handles external dollar payments via Stripe and external provisioning. They speak to each other only when the apprentice tier should grant credit deposits (none in v0.1).

## Endpoints

### Public

```
GET  /health                          health check (no auth)
GET  /apprentice/seats                live seats-filled count
                                      response: {"founding_filled": N, "founding_cap": 30, "total_active": M}

POST /apprentice/checkout             create Stripe Checkout Session
                                      body: {email, name, want_founding: bool, inviter?: str}
                                      response: {checkout_url}

POST /apprentice/webhook              Stripe webhook (HMAC verified)
                                      handles: checkout.session.completed,
                                               customer.subscription.created,
                                               customer.subscription.updated,
                                               customer.subscription.deleted

GET  /apprentice/status/{email}       lookup membership state
                                      response: {tier, active, founding, started_at}

GET  /apprentice/                     landing page (apprentice.html)
```

### Admin (X-Admin-Token)

```
POST /admin/refund/{stripe_session_id}        issue refund (30-day window)
POST /admin/replay-provisioning/{email}       re-run provisioning chain for an apprentice
GET  /admin/apprentices                       list all (CSV export option)
```

## Data store

SQLite at `/var/lib/apprentice-gateway/apprentice.db`:

```sql
CREATE TABLE apprentices (
  email TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  stripe_customer_id TEXT NOT NULL,
  stripe_subscription_id TEXT,
  tier TEXT NOT NULL DEFAULT 'apprentice',     -- 'apprentice'
  founding INTEGER NOT NULL DEFAULT 0,          -- 0 or 1
  founding_number INTEGER,                      -- 1-30 if founding, NULL otherwise
  active INTEGER NOT NULL DEFAULT 1,
  inviter TEXT,                                 -- Champion name who referred (for future affiliate layer)
  champion_number INTEGER,                      -- joined from champion-sign
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  provision_state TEXT NOT NULL DEFAULT 'pending'  -- 'pending' | 'partial' | 'complete' | 'failed'
);

CREATE TABLE provision_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  step TEXT NOT NULL,                           -- 'champion_card' | 'brain_account' | 'tg_invite' | 'welcome_email'
  status TEXT NOT NULL,                         -- 'success' | 'failed' | 'skipped' (feature flag off)
  detail TEXT,
  ts TEXT NOT NULL
);

CREATE TABLE stripe_events (
  event_id TEXT PRIMARY KEY,                    -- Stripe event ID for idempotency
  event_type TEXT NOT NULL,
  email TEXT,
  ts TEXT NOT NULL
);
```

## Stripe products (created by setup_stripe.py · run-once · idempotent)

| Product Name | Type | Price | Stripe Product ID | Notes |
|---|---|---|---|---|
| Champion Stack Apprentice | Recurring | $97/mo | TBD on creation | Live SKU |
| Champion Stack Apprentice — Founding | One-time | $497 | TBD on creation | Optional add-on · cap 30 · server-side enforced |

Both prices live in James's existing Stripe account (key already in `/etc/zen-village.env` · sk_live_<REDACTED>...). New env file `/etc/apprentice-gateway.env` will reuse same key.

## Provisioning chain

When `checkout.session.completed` webhook fires:

1. Insert apprentice row (with `provision_state='pending'`)
2. For each step (controlled by env flag):
   - `PROVISION_CHAMPION_CARD=1` → POST to champion-sign admin endpoint with `tier: apprentice`
   - `PROVISION_BRAIN_ACCOUNT=1` → POST to sunheart-brain admin endpoint creating user
   - `PROVISION_TG_INVITE=1` → POST to TG bot admin endpoint to add user to `@apprentices`
   - `PROVISION_WELCOME_EMAIL=1` → POST to mail pipeline with Haiku-drafted welcome
3. Update `provision_state` to `complete` (all 4 success) or `partial` (some failed) or `failed` (none succeeded)
4. If `partial` or `failed`: Telegram alert to James (so he can manually retry via `/admin/replay-provisioning/{email}`)

All four steps are idempotent so retries are safe.

## Feature flags (env-controlled)

```
PROVISION_CHAMPION_CARD=1        # default 1 once champion-sign admin endpoint exists
PROVISION_BRAIN_ACCOUNT=0        # default 0 until sunheart-brain user-create endpoint is verified
PROVISION_TG_INVITE=0            # default 0 until @apprentices channel exists + bot has admin
PROVISION_WELCOME_EMAIL=0        # default 0 until mail pipeline is verified
STRIPE_MODE=test                 # 'test' or 'live' · cutover after end-to-end test
FOUNDING_CAP=30                  # server-side cap enforcement
```

## Security

- All admin endpoints require `X-Admin-Token` header
- Stripe webhook signature verification mandatory (no bypass)
- Email is the primary key; we trust Stripe's email verification at checkout
- No raw card data ever touches our server (Stripe Checkout hosted)

## Account lapse policy (added 2026-05-19 per Counsel review v0.1 RED #1)

When a subscription lapses (cancellation · refund · failed payment after 30-day grace):

1. **Brain-server account** → marked inactive (read-only); data retained 90 days
2. **After 90 days** → vector memory + canonical files purged unless user requested export
3. **Champion seat** → preserved (Game state is permanent regardless of subscription status)
4. **TG channel** → user removed at next billing-cycle close
5. **Warning emails** → user receives 14-day, 7-day, 1-day warnings before purge
6. **Export endpoint** → `GET /apprentice/export/{email}` (X-User-Token authenticated) returns JSON dump of all personal data

Env flags governing lapse:

```
RETENTION_DAYS_AFTER_LAPSE=90    # purge brain-server data N days after subscription lapse
LAPSE_WARNING_DAYS=14,7,1        # send warning emails at these day counts before purge
```

## Legal compliance documents (added 2026-05-19 per Counsel review v0.1 RED #1 + RED #2)

Three legal pages are served by the gateway as static routes:

```
GET  /apprentice/privacy     Privacy Policy (CCPA + GDPR-baseline)
GET  /apprentice/terms       Terms of Service (binds IDS by reference)
GET  /apprentice/refund      Refund Policy (30-day full · 90-day pro-rated founding)
GET  /apprentice/ids         Income Disclosure Statement
```

Static HTML files live at:
- `static/privacy.html`
- `static/terms.html`
- `static/refund.html`
- `static/ids.html` (TBD — currently served from markdown source via `ids_v0.2.md` rendering)

Source-of-truth markdown templates at `core/INTENT/legal_templates/` (parameterized for reuse across Sunheart substrate products):
- `PRIVACY_POLICY_v1.md`
- `TERMS_OF_SERVICE_v1.md`
- `REFUND_POLICY_v1.md`

## Landing-page route variants (added 2026-05-19 per Counsel review v0.1 AMBER #6)

Two landing-page H1 variants exist for different audience contexts:

| Route | H1 voice | Audience | Source file |
|---|---|---|---|
| `/apprentice/` | Personal-voice ("I built a substrate...") | Warm cohort, soft-launch DMs | `static/apprentice.html` |
| `/apprentice/public` | Product-voice ("Champion Stack Apprentice — the AI life-OS substrate, productized") | Public-launch traffic, cold ads | `static/apprentice_public.html` |

The same checkout flow is shared. Only the H1 + meta description differ. Nginx routes both URLs to the gateway service.

Switching rule: cohort-DM emails link directly to `/apprentice/` (personal voice resonates with warm field). Any paid acquisition or open-web link uses `/apprentice/public` (regulator-defensive neutral framing).

## Clickwrap compliance (added 2026-05-19 per Counsel review v0.1 RED #2)

Checkout form requires two checkbox confirmations before Stripe Checkout opens:

1. "I have read and agree to the Terms of Service and Income Disclosure Statement."
2. "I have read the Privacy Policy and consent to brain-server account creation."

Both must be checked. JavaScript enforces; webhook payload includes `agreed_terms`, `agreed_privacy`, `agreed_at` timestamp. These fields are persisted in the `apprentices` table for audit purposes:

```sql
ALTER TABLE apprentices ADD COLUMN agreed_terms INTEGER NOT NULL DEFAULT 0;
ALTER TABLE apprentices ADD COLUMN agreed_privacy INTEGER NOT NULL DEFAULT 0;
ALTER TABLE apprentices ADD COLUMN agreed_at TEXT;  -- ISO timestamp of clickwrap event
ALTER TABLE apprentices ADD COLUMN ids_version TEXT;     -- IDS version they agreed to (e.g., 'v0.2')
ALTER TABLE apprentices ADD COLUMN tos_version TEXT;     -- TOS version they agreed to (e.g., 'v1.0')
ALTER TABLE apprentices ADD COLUMN privacy_version TEXT; -- Privacy version they agreed to (e.g., 'v1.0')
```

## Deploy

See `deploy.sh` and `apprentice-gateway.service`. Deploy chain:

```bash
# 1. Local sanity test
cd SERVICES/apprentice-gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
STRIPE_MODE=test STRIPE_SECRET_KEY=sk_test_... python -m uvicorn app.main:app --port 8772

# 2. Push to server
./deploy.sh

# 3. Server side: create products (run-once)
ssh root@198.54.123.234 'cd /opt/fpai/apps/apprentice-gateway && python3 app/setup_stripe.py'

# 4. Verify
curl https://fullpotential.com/apprentice/seats
```

## Reversibility

Every action is reversible:
- Stripe products: archive via Stripe Dashboard
- Service: `systemctl stop fpai-apprentice-gateway`
- Provisioning: feature flags off
- DB: file-based · backed up · can be restored
- Landing page: nginx alias removable

No data is irrecoverable. No commitment exceeds 30 days (refund window).

## Open work after Phase 1

- v0.2: Affiliate layer activation (Compressed Unilevel + Coded Generational tracking)
- v0.3: Concierge tier wiring ($497-997/mo · cap 10)
- v0.4: /becoming patron tier ($9/mo)
- v0.5: Member dashboard at `/apprentice/me`

---

*Designed by Ember · Trust-tier 4.1 reversible · pending James greenlight to deploy*
