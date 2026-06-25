# Subscription Billing v0.1 Pricing

Status: draft for James review. Do not create live Stripe Products or Prices from
this table until James approves final pricing.

| Tier | Draft Price | Daily Messages | Capabilities | CORA Bonus |
| --- | ---: | --- | --- | ---: |
| Free | $0/mo | 10 | search_web | 0 |
| Basic | $9/mo | 100 | search_web, email, calendar | 100 |
| Pro | $29/mo | Unlimited | all capabilities, priority routing | 500 |

## Launch Notes

- The free tier is real and useful, not a hobbled demo.
- Stripe is the PCI boundary. Store only Stripe customer/subscription IDs and
  local tier/status in `brain_index.user_agents`.
- `STRIPE_DISABLE=1` is the runtime kill switch for testing; payment processing
  is bypassed and users are treated as Basic.
- Upgrade prompts should be a door, not a wall. Use "you could" framing and keep
  the next action clear.

## Open Review Items

- James approves or revises the final monthly prices.
- James seeds Stripe Products and Prices manually, then sets
  `STRIPE_PRICE_BASIC_ID` and `STRIPE_PRICE_PRO_ID` in curator/index env.
- James confirms whether CORA bonuses are visible immediately at launch or held
  until CORA policy review is complete.
