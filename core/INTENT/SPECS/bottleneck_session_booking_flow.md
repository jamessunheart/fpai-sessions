# Bottleneck Session — Booking Flow Spec v1

**The technical path from "yes, I want one" → paid session on the calendar.** Minimum viable, no CRM, all reversible.

## Flow diagram

```
Outreach DM
    ↓
Landing page (/bottleneck)
    ↓
Pricing tier selection ($500 / $1,000 / $1,500)
    ↓
Stripe Payment Link (per tier)
    ↓
Stripe Checkout success →
    ↓
Cal.com booking page (with intake form)
    ↓
Booking confirmation email (auto, Cal.com)
    ↓
24hr reminder email (auto, Cal.com)
    ↓
Session delivered (Zoom link in calendar invite)
    ↓
Post-session: testimonial-ask email + Breakthrough Program info
    ↓
[Optional upsell flow]
```

## Stack — minimum viable

| Layer | Tool | Why | Cost |
|---|---|---|---|
| Landing page | Static HTML on fullpotential.ai/bottleneck | Already-owned domain · zero new ops surface | $0 |
| Payment | Stripe Payment Link (one per tier) | No code · refund-friendly · invoice auto-generated | 2.9% + 30¢ per txn |
| Booking | Cal.com (free tier) | Open source · embeddable · intake form built-in | $0 for solo |
| Confirmation/reminder email | Cal.com built-in | Bundled with booking | $0 |
| Session video | Zoom (existing) or Cal.com video | Either works · Zoom recording for testimonial | $0 if existing accounts |
| Tracking | Plausible / PostHog (existing if installed) | Privacy-friendly · simple funnel | $0 if existing |
| Client data | Single Airtable base (free tier) | Captures intake + status · no CRM lock-in | $0 |

**Total new monthly cost: $0** (just Stripe transaction fees on revenue).

## Stripe Payment Link configuration

Create 3 Payment Links · one per tier:

**Link A: Bottleneck Session — Solo ($500)**
- Product: "Full Potential Bottleneck Session — Solo"
- Description: "90-minute diagnostic + written Breakthrough Map"
- Price: $500 one-time
- Success URL: `https://cal.com/jamessunheart/bottleneck?tier=solo`
- Cancel URL: `https://fullpotential.ai/bottleneck#oops`

**Link B: Bottleneck Session — Small Team ($1,000)**
- Same as A but $1,000
- Success URL: `https://cal.com/jamessunheart/bottleneck?tier=team`

**Link C: Bottleneck Session — Established Business ($1,500)**
- Same as A but $1,500
- Success URL: `https://cal.com/jamessunheart/bottleneck?tier=biz`

Refund policy in Stripe metadata: "Full refund if session doesn't surface an actionable bottleneck."

## Cal.com event configuration

Single event type: `bottleneck-session`
- Duration: 90 minutes
- Location: Zoom (auto-generated link)
- Buffer: 15 min before, 15 min after (recovery)
- Availability: 3-5 slots/week (don't burn out; this is high-intensity work)
- Intake questions:
  1. Where you are now (1 paragraph)
  2. Where you want to be in 12 months (1 paragraph)
  3. What feels stuck (1 paragraph)
  4. Pricing tier confirmed
  5. How you heard about this

Reschedule policy: 1 free reschedule, then $100 reschedule fee.

## Email flows

### Booking confirmation (auto, Cal.com)
Subject: "Bottleneck Session booked — [date] at [time]"
Body:
> Thanks for booking. I'll see you [date] at [time] for 90 minutes.
>
> Two things before then:
> 1. Sit with the three intake questions — even just 10 minutes of reflection sharpens the call.
> 2. Block 30 minutes after the call to write down what surfaced before it fades.
>
> If you need to reschedule, click here: [link]. Zoom link is in the calendar invite.
>
> — James

### 24hr reminder (auto, Cal.com)
Subject: "Tomorrow: Bottleneck Session at [time]"
Body:
> Quick note — we're meeting tomorrow at [time]. Zoom link below.
>
> [Zoom link]
>
> If anything's come up since you filled the intake, jot it down. I want the latest version of where you are, not where you were a week ago.
>
> See you then.
>
> — James

### Post-session testimonial-ask (manual, +24hr after session)
Subject: "From yesterday's session"
Body:
> Hey [Name] — sending the Bottleneck Breakthrough Map [attached / linked].
>
> Two asks:
>
> 1. **First 3 actions** — share what you actually do (and don't) by Friday. Loop closes the value.
> 2. **One-line testimonial** if it landed for you. Verbatim, three sentences, what changed.
>
> If you want to keep moving — the Breakthrough Program is the 4-12 week container where we implement what we mapped. Numbers if you want them: [link to program details].
>
> Otherwise: ship the three actions and circle back when ready.
>
> — James

## Tracking

Airtable base "Bottleneck Sessions" with one row per booking:

| col | data |
|---|---|
| Name | from intake |
| Email | from Stripe/Cal.com |
| Phone | from intake |
| Tier paid | solo / team / biz |
| Amount paid | $500/$1000/$1500 |
| Session date | from Cal.com |
| Status | booked / delivered / map-sent / testimonial-received / upsell-engaged |
| Source | from intake "how heard" |
| Bottleneck identified | from session notes |
| Breakthrough Map link | Notion / Google Doc URL |
| Testimonial | once received |
| Upsell engaged | yes/no |
| Notes | freeform |

## Reversibility

- All flows are off-the-shelf SaaS · no custom code
- To kill the offer: pause Stripe links + remove Cal.com availability + redirect /bottleneck → homepage
- All data exports cleanly from Stripe/Cal.com/Airtable on shutdown

## Risks + safeguards

| Risk | Mitigation |
|---|---|
| Booking without paying | Stripe success URL is what shows the Cal.com calendar — can't book without payment |
| Refund disputes | Clear policy in Stripe + email · refund without resistance if asked |
| Calendar overload | Cap at 5/week in Cal.com availability |
| Quality drop from volume | First 10 sessions: pause new bookings after each to refine the diagnostic |
| Tier confusion | Strict mapping — solo = 1 person, team = 1-10 employees, biz = 10+ |

## Build sequence (Day 1-2 of 14-day launch)

1. Hour 1: Set up Stripe Payment Links (3 tiers)
2. Hour 2: Configure Cal.com event + intake questions
3. Hour 3: Build static landing page (HTML/Tailwind, deploy to fullpotential.ai/bottleneck)
4. Hour 4: Test end-to-end (book a test session, pay $1, verify all emails fire)
5. Hour 5: Set up Airtable base + tracking
6. Hour 6: Write reply-handling templates for outreach inbox
7. Hour 7: Polish copy based on test-booking experience
8. Hour 8: SHIP — page live, links live, ready for Day 3-7 outreach

Total: 8 focused hours over Days 1-2.

## Status

🟡 Draft v1 · 2026-05-24 02:15 CR · ready for James read · not yet built
