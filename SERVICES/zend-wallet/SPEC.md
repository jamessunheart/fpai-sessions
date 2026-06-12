# SPEC — ZEND Wallet (UC Credits)

**Service:** `zend-wallet`  
**Version:** 1.0.0  
**Port:** 8580  
**Purpose:** User-facing “Zend Money” wallet layer that uses **UC Credits** as prepaid internal fuel + gifting rail, with AI-assisted drafting.

---

## Canonical Protocol

- `docs/protocols/ZEND_REGENERATIVE_SPEC.md` (v2.0) — **PRIMARY**: Regenerative payments architecture
- `docs/protocols/ZEND_UC_CREDITS_SPEC.md` (v1.0) — UC Credits definition
- `docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md` (UC = 1:1 USD accounting, service credits)

---

## Core Responsibilities

1. **Show UC balance + unlocks** (calm UX metadata)
2. **Draft “Zend It” actions** from natural language (AI assistance)
3. **Execute UC transfers** via `fp-credits-gateway` (SSOT ledger)
4. **Invite + claim flow** for non-members (escrowed credits)

---

## Dependencies

- **Credits Gateway (SSOT)**: `fp-credits-gateway` on port `8765`
- **AI Brain** (optional): via Credits Gateway `/api/ai/query` or direct `/generate`

---

## Environment Variables

All env vars are prefixed with `ZEND_`.

- **ZEND_CREDITS_GATEWAY_URL**: default `http://localhost:8765`
- **ZEND_CREDITS_API_KEY**: required in production (service key with `read`, `transfer`, and optionally `debit`)
- **ZEND_ESCROW_ACCOUNT**: default `system:zend_escrow`
- **ZEND_FEES_ACCOUNT**: default `system:zend_fees`
- **ZEND_SERVICE_PORT**: default `8580`
- **ZEND_ZEND_ADMIN_KEY**: optional simple protection for early MVP

---

## API

### Health
- `GET /health`

### Wallet
- `GET /api/zend/wallet/{member_id}`
  - Returns UC balance (from Credits Gateway) + “unlocked” features list

### Draft (AI assistance)
- `POST /api/zend/draft-send`
  - Input: `member_id`, `prompt`
  - Output: parsed draft: recipient, amount_uc, note, risk flags, confirm level

### Execute
- `POST /api/zend/send`
  - Input: `from_member_id`, `to_member_id` OR `invite_contact`, `amount_uc`, `note`
  - If `invite_contact` provided, credits are escrowed to `system:zend_escrow`

### Invite Claim
- `POST /api/zend/invites/claim`
  - Input: `invite_code`, `claimer_member_id`
  - Transfers escrowed credits from `system:zend_escrow` to claimer

---

## Guardrails (MVP)

- Hard caps: amount <= 1000 UC per send (configurable later)
- Risk flags: large amount, new recipient, repeated sends
- “Send for me” always returns a draft requiring explicit confirm in MVP





