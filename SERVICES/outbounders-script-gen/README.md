# Outbounders AI Script Generator (MVP)

**Phase 1 of the Outbounders rebuild (per `core/INTENT/SPECS/outbounders_site_rebuild.md`).**

A free public tool that demonstrates "Outbounders, now AI-augmented" positioning.

## What it does

User describes their campaign in plain English:
- Industry / vertical
- Offer / product
- Target persona (job title, company size, geography)
- Goal of the call (book a meeting, qualify, sell direct, etc.)

→ AI returns:
1. An 800-word calling script with intro / value pitch / qualifying / close
2. 10 common objections with proven rebuttals
3. 5 qualifying questions for the prospect
4. A "next-steps" handoff script (book meeting / send follow-up email)

Optional: capture email to receive results, enroll in Outbounders.

## Stack

- **Frontend**: single HTML page (no framework) — `public/index.html`
- **Backend**: Cloudflare Worker calling Anthropic Claude API (Haiku for cost) — `worker/index.js`
- **Prompts**: versioned in `prompts/` (system + user templates)
- **Hosting**: Cloudflare Pages + Workers (free tier) OR Vercel Edge Function
- **Domain**: `script.outbounders.com` (subdomain on existing domain) OR `outbounders.com/ai-script-generator/`

## Tone

Linear × Beam — confident, operator-direct, no fluff. B2B sales-ops buyer audience.

## Cost projection

- Anthropic Claude Haiku: ~$0.003-0.005 per script generation
- Cloudflare Workers: free tier covers up to 100K requests/day
- Estimated cost at 100 daily generations: ~$10/month

## Deploy

1. `wrangler deploy` (after `wrangler login`)
2. DNS: add CNAME `script` → workers.dev URL via Cloudflare (5min)
3. Verify w/ end-to-end test
4. Embed link on `outbounders.com/` homepage as the "see what AI-augmented means" demo

## Not in MVP

- Email capture / lead routing (Phase 1.5)
- A/B testing variants (Phase 1.5)
- Premium tier ("Save your scripts", "Industry templates", etc.) — Phase 2
- Voice / IVR integration — Phase 3+
- Direct integration with `app.outbounders.com` campaign creation — Phase 2

## Success criteria

- Generates a usable script in <30 seconds
- Output is clearly better than ChatGPT-generic (uses Outbounders' domain expertise in the system prompt)
- Loads fast (<2s to first paint)
- Mobile-friendly
- Embeddable via iframe on outbounders.com homepage
