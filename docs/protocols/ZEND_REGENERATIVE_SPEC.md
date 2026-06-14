# ZEND Regenerative Payments — Canonical Specification

**Version:** 2.0.0  
**Status:** CANONICAL  
**Effective:** 2025-12-14  
**Authority:** Church of Consciousness / Cora Nation PMA  
**Maintainer:** Commons Ministry  

---

## Quick Lookup

| Question | Answer |
|----------|--------|
| **What is Zend?** | Ministry of Flow — regenerative payment facilitation |
| **What does Zend custody?** | Nothing. Money moves on partner rails (Stripe, Solana) |
| **What is UC?** | Internal prepaid service credits (1:1 USD, not money) |
| **How does it relate to Commons?** | Every send can earn TRUST, fees flow to Commons Reserve |
| **Settlement rails?** | Stripe (hosted checkout) + Solana USDC (wallet-signed) |
| **POS interface?** | Telegram/WhatsApp chat agent (ZendClerk) |

---

## Part 1: Vision & Philosophy

### 1.1 Constitutional Alignment

Zend operates under the Full Potential Constitution:

- **Optimization over Extraction**: Fees heal, fund, and empower — they circulate, never extract.
- **Autonomy over Dependency**: Users control their money; Zend facilitates but never custodies.
- **Consciousness over Computation**: "Zend to Ascend" — payment as spiritual practice, not stress.

### 1.2 The Two-Layer Model

| Layer | Purpose | Moves |
|-------|---------|-------|
| **External (Money)** | Settlement | Real USD/USDC via Stripe/Solana |
| **Internal (Ease)** | Experience | UC Credits for friction reduction, rewards, delegation |

**Locked Rule**: Money moves outside. Ease lives inside.

---

## Part 2: Core Primitives

### 2.1 ZendPaymentIntent

The canonical object representing "what the user wants to do":

```python
class ZendPaymentIntent:
    intent_id: str           # Unique identifier
    payer_id: str            # Member or guest identifier
    recipient_id: str        # Member, merchant, or invite placeholder
    amount: Decimal          # Amount in USD
    currency: str            # "USD" (display) — settles as USDC or USD
    rail_policy: str         # "stripe_first" | "solana_first" | "user_choice"
    commons_contribution_pct: int  # 0-5% opt-in tithe
    note: str                # Optional blessing message
    risk_score: float        # 0-1 (AI-assessed)
    confirm_level: str       # "none" | "light" | "full" | "human_review"
    status: str              # "draft" | "pending" | "confirmed" | "settled" | "expired" | "failed"
    created_at: datetime
    expires_at: datetime
    settled_at: datetime | None
    receipt: ZendReceipt | None
```

### 2.2 ZendLink (Blessing Links)

Shareable URL for payment requests:

- **Format**: `zend.to/<code>` or `zend.to/bless/<code>`
- **Resolves to**: ZendPaymentIntent with payer slot open
- **Metadata**: Sender name, blessing message, Commons badge, expiry

### 2.3 ZendReceipt

Immutable proof of settlement:

```python
class ZendReceipt:
    receipt_id: str
    intent_id: str
    rail: str                # "stripe" | "solana"
    external_ref: str        # stripe_payment_intent_id or solana_tx_signature
    amount_settled: Decimal
    commons_contributed: Decimal
    settled_at: datetime
    blessing_message: str | None
```

---

## Part 3: Regenerative Fee Circulation

### 3.1 Three-Flow Model

Every Zend transaction creates three value flows:

| Flow | Destination | Percentage | Purpose |
|------|-------------|------------|---------|
| 1. Ops | `system:zend_ops` | 40% | Infrastructure, partners, compliance |
| 2. Commons | `system:commons` | 30% | Commons Reserve Fund (needs-based benefits) |
| 3. Circulation | User UC wallets | 30% | Sponsored sends, experiences, priority |

**Configuration** (Credits Gateway):
```python
ZEND_FEE_OPS_PCT = 40
ZEND_FEE_COMMONS_PCT = 30
ZEND_FEE_CIRCULATION_PCT = 30
```

### 3.2 Fee Calculation

Base fee: 2.9% + $0.30 (Stripe passthrough) or 0.1% (Solana)

| Rail | Total Fee | Ops | Commons | Circulation |
|------|-----------|-----|---------|-------------|
| Stripe | 2.9% + $0.30 | 1.16% + $0.12 | 0.87% + $0.09 | 0.87% + $0.09 |
| Solana | 0.1% | 0.04% | 0.03% | 0.03% |

---

## Part 4: Trust Index Integration

### 4.1 Adaptive Ease

Zend reads Trust Index from `trust-index` service and adjusts UX:

| Trust Index | Posture | Confirmation Level | Sponsored Sends | Send for Me |
|-------------|---------|-------------------|-----------------|-------------|
| < 0.3 | Conservative | Full confirm + human review > $100 | None | Disabled |
| 0.3 - 0.7 | Balanced | Light confirm < $500 | 1/week | Draft only |
| > 0.7 | Generous | Light confirm < $2000 | 3/week | Enabled |

### 4.2 Emergency Freeze

Automatic system-wide freeze when:
- Trust Index < 0.2
- Manual trigger by Trustee/Council
- Anomaly detection (Town Crier alert)

---

## Part 5: Proof of Contribution

### 5.1 Send Actions Earn TRUST

Every completed Zend send logs to `contribution-tracker`:

| Action | Contribution Score |
|--------|-------------------|
| Successful send | +5 |
| First-time send to new recipient | +10 |
| Recipient claims invite | +50 (referral) |
| Opt-in Commons contribution (per UC) | +1 |
| Merchant receives payment | +3 |

### 5.2 Minimum for Benefits

Per TOKENS_STRATEGY.md: 100 contribution score per quarter qualifies for Commons Ministry benefits.

---

## Part 6: Experience Layer ("Zend to Ascend")

### 6.1 UC-Based Unlocks

| Lifetime UC Balance | Unlocks |
|---------------------|---------|
| 100+ | Meditation partner invite (1/month) |
| 250+ | Zen Village raffle entry |
| 500+ | "Send for Me" with AI delegation |
| 1000+ | Concierge human review (priority queue) |
| 2500+ | Founding Member badge + governance voice |

### 6.2 Implementation

Stored in Zend Wallet as:
```python
unlocked_experiences: List[str] = [
    "meditation_invite",
    "zen_village_raffle",
    "send_for_me",
    ...
]
```

**Critical Rule**: Access-based perks only. Never discounts or cash-equivalents.

---

## Part 7: Settlement Rails

### 7.1 Stripe Connector

- **Mode**: Hosted checkout (non-custodial)
- **Flow**: Create checkout session → redirect user → webhook confirms payment
- **Receipt**: Store `stripe_payment_intent_id` in ZendReceipt

### 7.2 Solana USDC Connector

- **Mode**: Wallet-signed payment request
- **Flow**: Generate payment request → user signs in wallet → verify tx signature
- **Receipt**: Store `solana_tx_signature` in ZendReceipt

### 7.3 Rail Selection

Default: `stripe_first` (broadest compatibility)

Override rules:
- If recipient has Solana wallet on file → offer Solana option
- If payer has Phantom/Solflare → offer Solana option
- User can always choose

---

## Part 8: POS ("Ministry of Flow")

### 8.1 ZendClerk Chat Agent

Interface: Telegram bot (v1), WhatsApp (v2)

**Merchant commands**:
```
/invoice 23.50 2 lattes + tip
/link           → generates ZendLink
/status <code>  → payment status
/today          → daily summary
```

### 8.2 Merchant Features

- **Opt-in Commons tithe**: Route 1-5% of each sale to Commons Reserve
- **Blessing receipts**: Include gratitude message option
- **Merchant TRUST**: Active merchants earn TRUST, qualify for Commons support

---

## Part 9: Hard Guardrails

| Guardrail | Value | Governance |
|-----------|-------|------------|
| Max single send | 10,000 UC | Trustee + Council |
| Max daily send per user | 25,000 UC | Hardcoded |
| Max Commons contribution | 5% | Hardcoded |
| Emergency freeze | Trust Index < 0.2 | Automatic |
| Human escalation | > 5,000 UC OR AI-flagged | Automatic |

---

## Part 10: Town Crier Alerts

Per Constitution: "Alerts must flag when a task risks sliding into extractive behavior."

| Alert | Trigger | Action |
|-------|---------|--------|
| High-frequency sends | > 10 sends/hour from single user | Flag for review |
| Large new recipient | > $500 to first-time recipient | Require extra confirmation |
| High dispute rate | Merchant > 2% disputes | Merchant review |
| Declining contribution | System-wide Commons rate < 10% | Dashboard warning |

---

## Part 11: AI Stewardship

### 11.1 Mandate

Per TOKENS_STRATEGY.md, AI in Zend operates as "Trustee Assistant":
- Operates within parameters set by Trustee/Council
- Cannot exceed hard guardrails
- Can be overridden by human at any time
- Transparent about reasoning

### 11.2 Explain Endpoint

`GET /api/zend/explain/{intent_id}` returns:
```json
{
  "intent_id": "...",
  "risk_score": 0.3,
  "confirm_level": "light",
  "reasoning": [
    "Amount ($50) is within normal range for sender",
    "Recipient is known contact (3 previous sends)",
    "Trust Index is 0.65 (Balanced posture)"
  ]
}
```

---

## Part 12: Partner Selection Criteria

| Criteria | Weight | Requirement |
|----------|--------|-------------|
| Non-custodial | 40% | Zend never holds user funds |
| Regenerative alignment | 30% | Prefers ESG/B-Corp/mission-driven |
| Developer experience | 20% | Clean APIs, webhooks, docs |
| Geographic coverage | 10% | Global reach preferred |

---

## Part 13: Legal & Compliance

### 13.1 Zend's Position

- **Does NOT** custody funds
- **Does NOT** transmit money (partners do)
- **Does NOT** promise returns
- **Does NOT** create stored monetary value

Zend is **software orchestration** — intent capture, safety, routing, receipts.

### 13.2 Required Disclaimers

All Zend-facing UI/docs must include:
```
UC is a prepaid service credit. 1 UC = $1.00 USD (fixed).
UC is not money, not an investment, and not redeemable for cash.
Zend does not custody funds. Money moves peer-to-peer via Stripe or Solana.
```

---

## Part 14: Service Architecture

### 14.1 Services

| Service | Port | Purpose |
|---------|------|---------|
| `zend-wallet` | 8580 | UC balance, unlocks, AI drafting |
| `zend-payments` | 8581 | PaymentIntent, ZendLink, receipts |
| `zend-clerk` | 8582 | Telegram/WhatsApp POS agent |

### 14.2 Dependencies

- `fp-credits-gateway` (8765): UC ledger SSOT
- `trust-index` (8560): Trust Index for adaptive ease
- `contribution-tracker` (8570): Proof of Contribution logging

### 14.3 Environment Variables

```bash
# Zend Wallet
ZEND_CREDITS_GATEWAY_URL=http://localhost:8765
ZEND_CREDITS_API_KEY=<service_key>
ZEND_TRUST_INDEX_URL=http://localhost:8560

# Zend Payments
ZEND_STRIPE_SECRET_KEY=<stripe_key>
ZEND_STRIPE_WEBHOOK_SECRET=<webhook_secret>
ZEND_SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Zend Clerk
ZEND_TELEGRAM_BOT_TOKEN=<bot_token>
```

---

## Part 15: Implementation Phases

| Phase | Scope | Why |
|-------|-------|-----|
| **v1.0** | ZendCore + ZendLink + Stripe + Trust Index read | Fastest GTM |
| **v1.1** | Solana USDC + Telegram POS | Non-custodial option + chat POS |
| **v1.2** | Contribution logging + TRUST integration | Every send = commons participation |
| **v1.3** | Experience layer (unlocks, invites) | "Zend to Ascend" becomes real |
| **v2.0** | Full fee circulation + Town Crier | Self-sustaining system |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12-14 | Regenerative integration, Commons alignment, Trust Index |
| 1.0.0 | 2025-12-13 | Initial UC Credits spec |

---

## For AI Agents

```python
# Canonical paths
ZEND_REGENERATIVE_SPEC = "docs/protocols/ZEND_REGENERATIVE_SPEC.md"
ZEND_UC_CREDITS_SPEC = "docs/protocols/ZEND_UC_CREDITS_SPEC.md"
UC_PROTOCOL = "docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md"
TOKENS_STRATEGY = "docs/protocols/TOKENS_STRATEGY.md"

# Quick summary
ZEND_ARCHITECTURE = {
    "zend-wallet": "UC balance + AI drafting (port 8580)",
    "zend-payments": "PaymentIntent + ZendLink + receipts (port 8581)",
    "zend-clerk": "Telegram/WhatsApp POS agent (port 8582)",
}

# Settlement rails
RAILS = ["stripe", "solana"]

# Fee circulation
FEE_SPLIT = {"ops": 40, "commons": 30, "circulation": 30}
```

---

**END OF SPECIFICATION**

*"Money moves outside. Ease lives inside. Fees heal, fund, and empower."*





