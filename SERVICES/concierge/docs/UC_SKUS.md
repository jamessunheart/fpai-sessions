# Concierge — Universal Credits SKUs (v1 draft)

All prices denominated in UC. 1 UC = $1.00 USD. Authority: `fp-credits-gateway`.

## Subscription tiers (monthly, billed in UC)

| SKU | Name | Price | Includes | Cap | Overage |
|---|---|---:|---|---|---|
| `concierge.starter.monthly` | Starter | 199 UC / mo | 1 number · AI inbound voice+SMS · human overflow · 200 AI-answered minutes | 200 min | 0.75 UC / min |
| `concierge.pro.monthly`     | Pro     | 499 UC / mo | 3 numbers · Starter + chat/email · warm transfer · 600 AI min · 100 human min · AI-QA + auto-training · outbound campaigns | 600 / 100 | 0.60 / 1.25 UC / min |
| `concierge.scale.monthly`   | Scale   | 1,499 UC / mo | Unlimited numbers · all features · skills-mesh routing · dedicated pod · 2,000 AI min · 400 human min | 2000 / 400 | 0.50 / 1.00 UC / min |

## Per-outcome (pay only when we deliver)

| SKU | Name | Price | Trigger |
|---|---|---:|---|
| `concierge.outcome.booked_job`   | Booked service visit | 12 UC | `bookings.status` → `confirmed` |
| `concierge.outcome.qualified_lead` | Qualified lead passed to client | 8 UC | conversation resolution=`qualified` |
| `concierge.outcome.answered_call` | After-hours answered call | 2 UC | voice conversation resolved by AI only |
| `concierge.outcome.human_handoff` | Human-assisted resolution | 4 UC | escalation.completed |

## Human hourly (network rates)

| SKU | Name | Price | Notes |
|---|---|---:|---|
| `concierge.human.bpo_hour`          | OneBPO agent hour          | 14 UC / hr | Base BPO floor time |
| `concierge.human.specialist_hour`   | Certified specialist hour  | 22 UC / hr | Vertical/skill-certified |
| `concierge.human.supervisor_hour`   | Live supervisor hour       | 35 UC / hr | On-demand escalation |

## Setup

| SKU | Name | Price |
|---|---|---:|
| `concierge.setup.onboarding`   | Onboarding (self-serve) | 0 UC (free with annual) |
| `concierge.setup.white_glove`  | White-glove onboarding  | 499 UC |

## Revenue share to agents (earnings ledger)

- Per-call: 40% of the outcome SKU charged on that conversation
- Hourly: 60% of the hourly SKU billed
- Bonuses: 10% tip pool from tenants who opt in

See `/SERVICES/fp-credits-gateway` for SKU registration + Stripe mapping.
