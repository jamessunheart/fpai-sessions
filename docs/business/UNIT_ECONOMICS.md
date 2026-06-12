# Full Potential Club - Unit Economics

> Last Updated: December 2024  
> Status: **APPROVED** ✅  
> The math works at every level.

---

## Service Cost Structure

| Service | Cost Driver | Cost/Unit | Price/Credit | Gross Margin |
|---------|-------------|-----------|--------------|--------------|
| 📞 Phone (Twilio) | ~$0.17/call | $0.17 | 1 credit ($1) | **83%** |
| 🐋 Whale Track | $40/mo API ÷ users | ~$0.02/day | 2 credits ($2) | **99%** |
| 🧠 AI API (Ollama) | ~$0.003/req | $0.003 | 0.03 credits | **90%** |
| 🧘 Wellness | ~$0.005/session | $0.005 | 0.5 credits | **99%** |
| 🖥️ Dashboard | ~$0.05/user/day | $0.05 | 2 credits ($2) | **97.5%** |

### Blended Credit Cost
Based on expected usage patterns:
```
40% Phone × $0.17  = $0.068
20% Whale × $0.02  = $0.004
20% AI    × $0.003 = $0.0006
10% Well  × $0.005 = $0.0005
10% Dash  × $0.05  = $0.005
──────────────────────────────
BLENDED COST/CREDIT = $0.08
```

**1 credit = $1.00 value to customer, $0.08 cost to us (92% margin)**

---

## Fixed Monthly Costs

| Item | Cost |
|------|------|
| Server (Hostinger VPS) | $15 |
| CoinGlass API | $40 |
| Twilio base | $10 |
| Mem0 API | $63 |
| Domain/SSL | $2 |
| Monitoring | $10 |
| **TOTAL** | **~$140/mo** |

**Breakeven**: 4 Builder members or 8 Explorer members

---

## Membership Tier Economics

### Explorer ($19/mo)
```
Revenue:           $19.00
Credit cost (50):  $4.00  (50 × $0.08)
Gross profit:      $15.00/mo
LTV (6 months):    $90.00
Max CAC:           $30.00
```

### Builder ($39/mo) ← Most Popular
```
Revenue:           $39.00
Credit cost (150): $12.00 (150 × $0.08)
Gross profit:      $27.00/mo
LTV (6 months):    $162.00
Max CAC:           $54.00
```

### Founder ($99/mo)
```
Revenue:           $99.00
Credit cost (500): $40.00 (500 × $0.08)
Gross profit:      $59.00/mo
LTV (6 months):    $354.00
Max CAC:           $118.00
```

---

## Referral Bonus Structure

### What Referrer Gets

| Friend's Action | Referrer Credits | Our Cost |
|-----------------|------------------|----------|
| Starts free trial | +5 | $0.40 |
| → Explorer ($19) | +15 | $1.20 |
| → Builder ($39) | +25 | $2.00 |
| → Founder ($99) | +50 | $4.00 |
| Stays 3+ months | +25 | $2.00 |
| Top referrer/mo | +100 | $8.00 |

### What Friend Gets (Signup Bonus)

| Tier | Bonus Credits | Our Cost |
|------|---------------|----------|
| Free trial | +10 | $0.80 |
| Explorer | +25 | $2.00 |
| Builder | +50 | $4.00 |
| Founder | +100 | $8.00 |

### Revenue Share (Founder Tier)

- **Founder (10%)**: Friend pays $39/mo → Referrer gets $3.90/mo in credits
- **Annual Founder (15%)**: Friend pays $39/mo → Referrer gets $5.85/mo in credits
- This is **recurring** as long as friend stays a member

---

## Net Acquisition Math

### Friend → Builder ($39/mo)
```
First month revenue:        $39.00
Referrer bonus:            -$2.00  (25 credits)
Friend bonus:              -$4.00  (50 credits)
Credit fulfillment:       -$12.00  (150 base credits)
──────────────────────────────────
NET DAY 1:                 $21.00  ✅
```

### Worst Case: Max Earning Builder
```
Revenue:                    $39.00
Base credits (150):        -$12.00
Max engagement earned:      -$9.20  (115 credits)
──────────────────────────────────
NET:                        $17.80 (46% margin) ✅
```

**Even members who maximize credit earning are still profitable.**

---

## Engagement Credit Limits

| Action | Credits | Monthly Cap | Max Cost |
|--------|---------|-------------|----------|
| Weekly call | +5 | 4/mo = 20 | $1.60 |
| Share win | +5 | 4/mo = 20 | $1.60 |
| Help member | +10 | 4/mo = 40 | $3.20 |
| Testimonial | +25 | 2 total | $2.00 |
| Video testimonial | +50 | 1 total | $4.00 |
| Create guide | +50 | 1/mo = 50 | $4.00 |

**Max monthly engagement earnings: ~115 credits ($9.20 cost)**

---

## Key Metrics to Track

### Unit Economics
- [ ] Blended credit cost (target: <$0.10)
- [ ] Credit redemption rate (expect: 60-80%)
- [ ] LTV:CAC ratio (target: >3:1)

### Growth
- [ ] Member count by tier
- [ ] Monthly referrals
- [ ] Referral conversion rate
- [ ] Churn rate (target: <10%/mo)

### Engagement
- [ ] Weekly call attendance
- [ ] Credit earning rate
- [ ] Testimonial collection rate

---

## Pricing Guardrails

### Never Go Below
- Explorer: $15/mo (margin floor)
- Builder: $29/mo (margin floor)
- Founder: $79/mo (margin floor)

### Credit Giveaway Limits
- Max signup bonus: 100 credits
- Max referral bonus: 50 credits
- Max engagement/month: 150 credits

### Revenue Share Caps
- Regular members: None (no revenue share)
- Founder: 10% max
- Annual Founder: 15% max

---

## Summary

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   1 Credit = $1.00 value, $0.08 cost                │
│   92% margin on every credit redeemed               │
│                                                     │
│   Breakeven: 4 Builder members                      │
│   Target: 100 members = $2,700/mo profit            │
│                                                     │
│   THE MATH WORKS ✅                                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```












