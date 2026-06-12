# Apprentice Gateway

Stripe checkout + provisioning for **Champion Stack Apprentice** ($97/mo subscription · optional $497 founding tier · cap 30 founding).

**Port:** 8772
**Status:** Phase 1 code complete · NOT deployed
**Spec:** `SPEC.md`

## Quick reference

```
GET  /apprentice/seats     → live founding-30 counter
POST /apprentice/checkout  → Stripe Checkout Session
POST /apprentice/webhook   → Stripe webhook + provisioning
GET  /apprentice/status/{email} → membership lookup
```

## Local dev

```bash
cd SERVICES/apprentice-gateway
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# .env (do not commit)
cat > .env <<'EOF'
STRIPE_MODE=test
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...
ADMIN_TOKEN=local-dev-token
DB_PATH=./apprentice.db
PROVISION_CHAMPION_CARD=0
PROVISION_BRAIN_ACCOUNT=0
PROVISION_TG_INVITE=0
PROVISION_WELCOME_EMAIL=0
FOUNDING_CAP=30
LANDING_BASE_URL=http://localhost:8772
CHECKOUT_SUCCESS_URL=http://localhost:8772/apprentice/welcome
CHECKOUT_CANCEL_URL=http://localhost:8772/apprentice/
EOF

export $(cat .env | xargs)
uvicorn app.main:app --port 8772 --reload
```

Then in another shell:
```bash
# Create products (run once · idempotent · safe to re-run)
python app/setup_stripe.py
```

## Production deploy

```bash
./deploy.sh
```

Deploys to `/opt/fpai/apps/apprentice-gateway` on `198.54.123.234`, installs systemd unit `fpai-apprentice-gateway.service`, reloads nginx with new location block at `/apprentice/`.

## Stripe webhook setup

After deploy:
1. In Stripe Dashboard → Developers → Webhooks → Add endpoint
2. URL: `https://fullpotential.com/apprentice/webhook`
3. Events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
4. Copy signing secret → `/etc/apprentice-gateway.env` → `STRIPE_WEBHOOK_SECRET=whsec_...`
5. Restart: `systemctl restart fpai-apprentice-gateway`

## Provisioning feature flags

All four provisioning steps are feature-flagged. Default state: ALL OFF in production.

Turn on one at a time after verifying each:

```bash
# Champion card update (requires champion-sign admin endpoint)
PROVISION_CHAMPION_CARD=1

# Brain server account (requires sunheart-brain user-create endpoint verified)
PROVISION_BRAIN_ACCOUNT=1

# TG channel invite (requires @apprentices channel + bot admin)
PROVISION_TG_INVITE=1

# Welcome email (requires mail pipeline verified)
PROVISION_WELCOME_EMAIL=1
```

If any step fails for a paid apprentice, James gets a TG alert. Manual retry via:
```bash
curl -X POST https://fullpotential.com/apprentice/admin/replay-provisioning/foo@bar.com \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

## What this is NOT

- NOT the internal credits ledger (that's `fp-credits-gateway` port 8765)
- NOT the WPA signing service (that's `champion-sign` port 8770)
- NOT the brain server itself (that's `sunheart-brain`)
- NOT a generic Stripe service (it's specific to Apprentice product)

## Files

```
SERVICES/apprentice-gateway/
├── README.md                      this file
├── SPEC.md                        full design spec
├── requirements.txt               python deps
├── deploy.sh                      push to server + systemd install
├── apprentice-gateway.service     systemd unit
├── app/
│   ├── __init__.py
│   ├── main.py                    FastAPI app
│   ├── db.py                      sqlite layer
│   ├── provisioning.py            4-step chain · feature-flagged
│   └── setup_stripe.py            run-once product creator
└── static/
    └── apprentice.html            landing page (draft hero copy)
```
