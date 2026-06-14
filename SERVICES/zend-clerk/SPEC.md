# SPEC — Zend Clerk (POS Chat Agent)

**Service:** `zend-clerk`  
**Version:** 1.0.0  
**Port:** 8582  
**Purpose:** Telegram (and future WhatsApp) bot for merchant POS operations. "Ministry of Flow" - regenerative commerce facilitation.

---

## Canonical Protocol

- `docs/protocols/ZEND_REGENERATIVE_SPEC.md` Part 8 — **PRIMARY**

---

## Core Responsibilities

1. **Quick invoice creation** via chat commands
2. **ZendLink generation and sharing**
3. **Payment status tracking**
4. **Daily summaries**
5. **UC balance checking**

---

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Register as merchant | `/start` |
| `/invoice <amount> <description>` | Create payment request | `/invoice 23.50 2 lattes + tip` |
| `/link` | Get last ZendLink | `/link` |
| `/status <code>` | Check payment status | `/status abc123` |
| `/today` | Daily summary | `/today` |
| `/balance` | Check UC balance | `/balance` |

---

## Natural Language Support

The bot also supports natural language invoice creation:
- `23.50 2 lattes + tip` → Creates invoice for $23.50
- `50 for consultation` → Creates invoice for $50.00

---

## Dependencies

- `zend-payments` (8581): Invoice creation, link resolution
- `zend-wallet` (8580): UC balance checking

---

## Environment Variables

```bash
ZEND_CLERK_TELEGRAM_BOT_TOKEN=<bot_token>
ZEND_CLERK_ZEND_PAYMENTS_URL=http://localhost:8581
ZEND_CLERK_ZEND_WALLET_URL=http://localhost:8580
```

---

## Merchant Features

Per ZEND_REGENERATIVE_SPEC.md Part 8.2:

- **Opt-in Commons tithe**: Merchants can route 1-5% of each sale to Commons Reserve
- **Blessing receipts**: Receipts include sender/receiver names + optional gratitude message
- **Merchant TRUST**: Active merchants earn TRUST, qualify for Commons support

---

## Roadmap

- **v1.0**: Telegram bot (current)
- **v1.1**: WhatsApp integration via Twilio
- **v2.0**: Voice assistant integration





