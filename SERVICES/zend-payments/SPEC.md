# SPEC — Zend Payments (External Settlement)

**Service:** `zend-payments`  
**Version:** 1.0.0  
**Port:** 8581  
**Purpose:** External settlement layer handling PaymentIntent, ZendLink resolution, and receipts via partner rails (Stripe/Solana).

---

## Canonical Protocol

- `docs/protocols/ZEND_REGENERATIVE_SPEC.md` (v2.0) — **PRIMARY**
- `docs/protocols/ZEND_UC_CREDITS_SPEC.md` (v1.0)

---

## Core Responsibilities

1. **PaymentIntent management** — Create, track, confirm, cancel payment intents
2. **ZendLink resolution** — `zend.to/<code>` → payment details + available rails
3. **Settlement via Stripe** — Hosted checkout (non-custodial)
4. **Settlement via Solana** — Wallet-signed USDC payment requests
5. **Receipt storage** — Immutable proof of settlement

---

## Relationship to zend-wallet

| Layer | Service | Purpose |
|-------|---------|---------|
| Internal (UC) | `zend-wallet` | UC balance, AI drafting, experience unlocks |
| External (Money) | `zend-payments` | Real USD/USDC settlement via partners |

**Key principle**: Money moves outside (via zend-payments). Ease lives inside (via zend-wallet).

---

## API

### Health
- `GET /health`

### Payment Intents
- `POST /api/intents` — Create payment intent, returns ZendLink
- `GET /api/intents/{intent_id}` — Get intent details
- `POST /api/intents/{intent_id}/confirm` — Confirm settlement (Stripe webhook or Solana tx)
- `POST /api/intents/{intent_id}/cancel` — Cancel pending intent

### ZendLink
- `GET /api/links/{code}` — Resolve ZendLink to intent details
- `GET /{code}` — Redirect to Stripe checkout or payment page

### Receipts
- `GET /api/receipts/{receipt_id}` — Get settlement receipt
- `GET /api/receipts/intent/{intent_id}` — Get receipt by intent

### Webhooks
- `POST /webhooks/stripe` — Stripe payment confirmation webhook

### POS / Merchant
- `POST /api/invoices` — Create merchant invoice (for Telegram/WhatsApp bot)
- `GET /api/qr/{code}` — Generate QR code for ZendLink

---

## Environment Variables

```bash
# Service
ZEND_PAYMENTS_SERVICE_PORT=8581
ZEND_PAYMENTS_DATABASE_URL=sqlite+aiosqlite:///./zend_payments.db

# Credits Gateway
ZEND_PAYMENTS_CREDITS_GATEWAY_URL=http://localhost:8765
ZEND_PAYMENTS_CREDITS_API_KEY=<service_key>

# Stripe
ZEND_PAYMENTS_STRIPE_SECRET_KEY=<stripe_key>
ZEND_PAYMENTS_STRIPE_WEBHOOK_SECRET=<webhook_secret>
ZEND_PAYMENTS_STRIPE_ENABLED=true

# Solana
ZEND_PAYMENTS_SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
ZEND_PAYMENTS_SOLANA_ENABLED=true

# ZendLink
ZEND_PAYMENTS_ZENDLINK_BASE_URL=https://zend.to
```

---

## Guardrails

Per `ZEND_REGENERATIVE_SPEC.md` Part 9:

| Guardrail | Value |
|-----------|-------|
| Max single intent | 10,000 USD |
| Max daily per merchant | 100,000 USD |
| Intent expiry | 30 minutes default |
| Commons contribution max | 5% |

---

## Settlement Flow

```
1. User/Merchant creates PaymentIntent via API
2. Service generates ZendLink and Stripe checkout (if enabled)
3. Payer opens ZendLink → redirected to Stripe checkout
4. Payer completes payment
5. Stripe webhook confirms → Intent marked SETTLED
6. Receipt created with external_ref (stripe_payment_intent_id)
7. (Optional) Commons contribution collected via fp-credits-gateway
```

---

## Dependencies

- `fp-credits-gateway` (8765): Zend fee collection, Commons funding
- `zend-wallet` (8580): UC operations (separate service)
- `trust-index` (8560): Optional — adaptive risk assessment





