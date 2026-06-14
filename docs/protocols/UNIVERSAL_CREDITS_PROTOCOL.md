# UNIVERSAL CREDITS (UC) — PROTOCOL

**Version:** 1.0.0  
**Status:** Canonical  
**Purpose:** Define UC as the system-wide spend/credits rail used for pricing, payments, and accounting across Full Potential OS.

---

## 1) The One Rule (Locked)

**1 UC = $1.00 USD (fixed, always).**

UC is a **service credit / usage credit**, not money.

---

## 2) What UC Is / Is Not

### UC **IS**
- A **prepaid internal credit** for services (AI, software, concierge, etc.)
- A **pricing unit** across the ecosystem
- An **accounting rail** (ledger entries, not cash)

### UC **IS NOT**
- Cash or a bank deposit
- A transferable currency for public markets
- Yield-bearing
- Redeemable for fiat (no cash-out promise)
- An investment product

---

## 3) Phases (Roadmap)

UC evolves by phases, but the **One Rule** remains fixed:

- **Anchor** (current): 1 UC = $1, fixed; focus on reliability + adoption  
- **Stabilization**: stronger guardrails, audits, and budget controls  
- **Sovereignty**: mature governance + safety brakes; stronger treasury autonomy  
- **Transition**: controlled migration paths for legacy credit terms (aliases)

---

## 4) Canonical Implementation (SSOT)

**Service:** `fp-credits-gateway` (Credits Gateway)  
**Role:** Single source of truth for:
- credit pricing
- exchange/alias behavior
- protocol version + phase
- ledger balances and transfers

### Required API calls (do not hardcode)
- **Protocol status**: `GET /api/protocol`
- **Exchange rates** (aliases/pricing): `GET /api/exchange-rates`
- **Pricing**: `GET /api/pricing`

> Engineering rule: **never hardcode** UC value or exchange behavior in downstream services. Always read from Credits Gateway.

---

## 5) Aliases / Legacy Names

Some services historically used different labels for the same 1:1 credit.

**Policy:** Aliases may exist for compatibility, but UX should standardize on **UC**.

---

## 6) Required Language (Compliance)

All UC-facing UI/docs should include:

```
UC is a prepaid service credit. 1 UC = $1.00 USD (fixed).
UC is not money, not an investment, and not redeemable for cash.
```

---

## 7) Design Principles

- **Clarity > complexity**
- **No volatility UX** (no charts, no “price” talk)
- **Safety guardrails** (caps, holds, audit trails)
- **Outcome-driven** (credits should drive real value delivered)

---

**END OF PROTOCOL**




