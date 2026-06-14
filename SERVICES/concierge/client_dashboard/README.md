# client-dashboard

Next.js 14 client-side dashboard for tenant admins.

Scope (v1):
- Self-serve onboarding wizard (URL → knowledge → trial number → Stripe checkout)
- Live metrics (calls answered, books, AI vs human, compliance pass rate)
- Transcript search + replay
- Settings: business hours, persona, tools, feature flags, team
- Billing hook into `fp-credits-gateway`

Run: `npm install && npm run dev` (port 3101). Planned in Milestone M2.
