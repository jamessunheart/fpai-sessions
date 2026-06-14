# Spec — Outbounders Signup Friction Reduction

**Status:** Draft — not deployed. Spec only. Production app.outbounders.com untouched.
**Date:** 2026-05-23
**Author:** AI (Ember)
**Target:** `app.outbounders.com/signup`

## Current state (audited 2026-05-23)

Signup requires:
- Email
- Country
- Password + repeat password
- Phone number
- **5 separate required checkboxes** covering:
  - Requirements document
  - Non-circumvention clause (penalties for direct contracting)
  - Confidentiality
  - Role-specific terms (separate for agents vs clients)
  - General TOS
- Role choice (Employer vs Outbounder)
- "I agree that you have read..." phrasing (awkward legalese)

## Why it's hurting conversion

Aligned with the 23× signup decline (1,756/mo → 75/mo, 2025→2026):
- **Cognitive load**: 5 checkboxes interrupts the flow at peak intent
- **Legal language as first impression**: non-circumvention warnings before product value is established = trust killer
- **No pricing visible**: users must commit before seeing what they're paying
- **Dual-audience confusion**: split role flow doubles the form complexity

## Proposed redesign

### Step 1 — Role selector (one tap, no form)
Two big buttons on first screen:
- **"I want to hire outbounders"** → continues to client signup
- **"I want to find work"** → continues to agent signup

No fields yet. Just intent capture.

### Step 2 — Role-specific 3-field form
**Client path:** Email · Password · Country
**Agent path:** Email · Password · Country · Phone

### Step 3 — Single agreement
ONE checkbox:
> ☐ I agree to the [Terms of Service](/terms), [Privacy Policy](/privacy), and [Non-Circumvention Agreement](/nca) (Outbounders.com).

The 5 separate concerns get collapsed into ONE master agreement. The individual docs remain linked for users who want to read them. The non-circumvention clause specifically gets pulled OUT of the signup form and shown as a one-time modal AFTER account creation, just before they post their first campaign / accept their first job.

### Step 4 — Onboarding tour (post-signup)
Skip-able 4-step tour:
1. (Client) How to post a campaign / (Agent) How to find work
2. Pricing model (transparent — $25 deposit, hourly rates, platform fee)
3. Payment + safety (funds held until work delivered)
4. Get started CTA

## Expected impact

Conservative: +20% signup completion (industry standard for friction reduction at this magnitude)
Aggressive: +40-60% (closer to industry leaders for similar marketplaces — Upwork, Fiverr)

If signups recover to even half of Jan 2025 levels (~875/mo), and 1% activate to paying clients within 60 days, that's ~9 new paying clients/month — DOUBLING the current active client base.

## Implementation notes

1. App stack is CodeIgniter (PHP). Signup controller likely at `/home/obapp/public_html/app/users/application/controllers/` (verify before edit).
2. Non-circumvention modal pattern: WordPress-style "first-run dialog" gated by `users.first_campaign_at` or `users.first_application_at`.
3. A/B test option: route 50% of new traffic to legacy signup, 50% to new flow, measure 7-day conversion to first deposit (client) or first application (agent).

## Open questions for James

- Should the non-circumvention clause modal block first action, or be acknowledged-and-warned (softer)?
- Pricing visibility — comfortable showing platform fee % explicitly, or keep it bundled in displayed rates?
- Onboarding tour copy — happy to draft, but you may want voice/positioning alignment first.

## Not in this spec (deliberately out of scope)

- The marketplace UX inside the platform (search, filter, hire flow)
- Mobile responsiveness audit
- Payment method expansion (crypto, ACH)
- Localization (currently English-only)

Each of these is its own spec.
