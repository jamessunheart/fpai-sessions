# Spec — Outbounders.com Site Rebuild

**Status:** Draft — pending James's call on brand positioning.
**Date:** 2026-05-23
**Author:** AI (Ember)
**Target:** Marketing site `outbounders.com` (WordPress on legacy `outbndrs_home` DB · `/home/outbndrs/public_html/`)
**Out of scope:** `app.outbounders.com` (live production CodeIgniter app · separate spec).

## Current state (audited 2026-05-23)

- Running WordPress with the **StartIt qodeinteractive theme** (purchased 2014-era)
- **17 published pages** after today's cleanup (down from 77)
- **60 theme-demo pages demoted to draft** (Standard Style, Gallery, Conference Home, Tech Business, etc.) — preserved in DB, rollback table at `_backup_2026_05_23_page_status`
- Active main menu: 4 items (Jobs / Browse Agents / Login / Signup) — clean
- Homepage = page ID 7378 "Main Home v2"
- `/pricing` rebuilt today (Lorem Ipsum → real page)
- `/app` → 301 to `app.outbounders.com/`
- All Lorem Ipsum subtitles cleared

## Why rebuild

1. **StartIt theme = 2014 visual language.** Trust signal is "this is an old website built by someone who didn't care."
2. **No content engine.** Blog is empty. No SEO surface. No case studies. No ROI calculator.
3. **23× signup decline** correlates with the site's neglected state.
4. **AI-augmentation is the wedge** (per James 2026-05-23 strategic call). Current site doesn't communicate any 2026 differentiation vs Upwork/Fiverr.

## Brand-positioning options (PICK ONE — gates the rest)

| Option | Brand | Positioning | Notes |
|--------|-------|------------|-------|
| **A. Modernize** | Outbounders.com | "Hire AI-augmented outbound sales reps · $25 to start" | Keeps domain equity · adds "AI-augmented" badge · lowest risk |
| **B. Subdomain pivot** | Outbounders.ai or ai.outbounders.com | "Outbounders, now AI-augmented" | Signals new era · risks SEO fragmentation |
| **C. Niche it** | Outbounders for B2B SaaS / Real Estate / etc | "Cold-call agents trained for [niche]" | Higher conversion · smaller TAM · best for premium pricing |
| **D. Full rebrand** | New name + domain | Total reset | Highest risk · maximum freedom · 6-12mo SEO recovery |

**Recommendation: Option A.** Outbounders.com has 11+ years of domain equity, brand searches, link history. Position as "Outbounders — now AI-augmented" inside the existing brand. Adds the differentiator without risking the foundation. Options B-D can come later if needed.

## Page-by-page rebuild plan (assuming Option A)

### Tier 1 — Critical conversion pages (rebuild from scratch)

| Page | Slug | Current | Rebuild to |
|------|------|---------|-----------|
| Home | / (page 7378) | Elementor StartIt layout | Hero → Social Proof → AI-Augmentation Pitch → 3-step How-It-Works → Live Calculator → Pricing → CTA |
| Pricing | /pricing/ (page 469) | Fixed today (clean) | Add ROI calculator + per-feature comparison table |
| Contact | /contact/ (page 598) | Has Lorem in subtitle (cleaned today) | Simplify · just email + Calendly + Telegram |
| Sign Up gateway | (currently external) | Direct to app.outbounders.com/signup | Add pre-signup pricing reveal + role-aware preview |

### Tier 2 — Trust + Value pages (rewrite content, keep slugs)

| Page | Slug | Current | Rebuild to |
|------|------|---------|-----------|
| About Us | /about-us/ (page 366) | Real content, 2014-era voice | Story · why-now (AI-era) · founder · team |
| Who Are We | /who-are-we/ (page 7277) | Generic copy | Merge into About Us · redirect |
| Benefits for Clients | /benefits-for-clients/ (page 7259) | Real, dated | Refresh w/ AI-augmentation framing + case studies |
| Benefits for Jobseekers | /benefits-for-jobseekers/ (page 7264) | Real, dated | Refresh w/ "AI-coached agent" value prop |
| Comparison | /oubounders-com-comparison/ (page 7269) | Typo in slug! Real content | Fix slug · update comparison vs Upwork / Fiverr / Apollo / Outreach |
| FAQ | /faq/ (page 554 — DEMOTED today) | Was Lorem | NEW page · 12-15 real questions from support history |

### Tier 3 — Content engine (NEW — currently empty)

| Page | Slug | Purpose |
|------|------|---------|
| ROI Calculator | /roi/ | "$25 = X calls = $Y if you close 1%" · interactive · embeddable |
| Case Studies | /case-studies/ | 3-5 real customer stories (need James to identify candidates) |
| Cold Calling Guide | /guide/cold-calling/ | Cornerstone SEO content · 4-6K words · ranks for "how to outsource cold calling" |
| AI Scripts Library | /scripts/ | Pre-built outbound scripts by industry · gated for email capture |
| Blog | /blog/ | Weekly cadence · AI-generated + human-edited |

### Tier 4 — Legal (keep, light refresh)

- Terms of Use, Privacy Policy, Disclaimer — review for current accuracy, no rebuild

## Visual + UX direction

- Drop StartIt theme entirely
- Modern minimalist: Stripe / Linear / Vercel design language
- Mobile-first
- Dark mode toggle
- One-page-style scrolling on home with sticky CTA
- System font stack (no FOIT/FOUT)
- Page Speed Index target: <2s on 3G

## Technical decisions

| Decision | Recommendation | Why |
|----------|---------------|-----|
| Keep WordPress? | **NO** — migrate to static (Astro / Next.js) | Faster · cheaper · easier to AI-iterate |
| Hosting | Vercel or Cloudflare Pages | Free tier covers it · global CDN built-in |
| CMS | Markdown files in repo OR Sanity headless | AI can edit markdown directly |
| Forms | Cloudflare Forms or Formspree | Free tier · no backend needed |
| Analytics | Plausible (privacy-first) or Cloudflare Analytics | No cookie banner · GDPR-clean |
| Search Console | Set up properly with sitemap.xml | Diagnose the 23× decline + measure recovery |

## Migration safety

- Keep the WordPress instance LIVE during rebuild on a staging subdomain (`new.outbounders.com`)
- Test all URLs + redirects against the old site's published page list
- Set up 301 redirects from any retained-from-WP slugs → new slugs
- Run side-by-side for 1 week, then switch DNS
- Keep WordPress as a 90-day fallback before decommissioning

## Estimated effort

| Phase | Wks | Who |
|-------|----:|-----|
| Design + brand pass (Option A) | 1 | AI + James review |
| Tier 1 pages (Home, Pricing, Contact, Signup gateway) | 1-2 | AI |
| Tier 2 pages (rewrite) | 1 | AI |
| Tier 3 content engine (5 pages + calculator) | 2 | AI |
| Migration + redirects + testing | 1 | AI |
| **Total** | **6-7 wks** | AI-led, James reviews at each phase |

## Open questions for James

1. **Brand positioning** — A, B, C, or D from the table above?
2. **Real customer case studies** — who would let us write about them?
3. **Tone / voice** — confident-startup vibe (Linear), warm-craft vibe (Hatch), or operator-direct (Beam)?
4. **Pricing fee transparency** — comfortable disclosing the platform's % cut publicly?
5. **AI-augmentation features to ship FIRST** — script generator? call coaching? matching?

## Dependencies

- AI-augmentation Phase 1 (script generator) needs to be working before site claims it
- Google Search Console access needed to forensic the 23× decline + measure recovery
- Decision on `app.outbounders.com` — keep as-is or also modernize? (separate spec)
