# Studio Site Outline — Apprentice Studio

> **DRAFT — for human review.**
>
> Single-page site for v0. Expand after cohort 1 ships.

## Domain

Suggested: `apprentice.fpai.com` or `studio.fullpotential.ai` (pick whichever is cleanest with existing brand).

## Page structure (single page, scroll)

### 1. Hero

**Headline:**
> Most AI is being built to replace humans.
> We're training builders to make AI that expands them.

**Sub:**
> The Apprentice Studio is a 10-week AI-native program where small cohorts ship regenerative products inside Full Potential AI.

**CTAs:**
- `Apply for Cohort 1` (active during application window)
- `Read the Manifesto`

### 2. What it is

Three columns:

| Living Lab | AI as Co-Builder | Apprentices Keep What They Build |
|---|---|---|
| Not a school. A studio with apprenticeships. Real products, real revenue, real impact. | Every apprentice gets Aria — a permanent AI collaborator. The first studio where AI is staff, not subject matter. | 70% to apprentice, 20% to studio, 10% to shared cohort pool. Regenerative by design. |

### 3. The 10-week shape

Visual timeline:
- Week 1 — Onsite kickoff retreat
- Weeks 2-9 — Remote build sprint (ship by week 8)
- Week 10 — Onsite demo retreat + public showcase

### 4. Three lenses

> Every product we ship hits at least two:
> *Regenerative* · *Sovereignty-respecting* · *Consciousness-expanding*

### 5. Cohort 1

- Size: 4-6 apprentices
- Tracks: [3 tracks, populated when human approves from 90-day plan]
- Application window: [dates]
- Cohort starts: [date]
- Demo day: [date]

### 6. What you get / what we ask

Two columns from the manifesto's "What you get" and "What we ask" sections.

### 7. Selection process

Three-stage filter, briefly:
1. Application + portfolio
2. 48-hour build challenge
3. Conversation

> We reject most applicants. That's not personal — scarcity is part of how this program works.

### 8. The studio team

- Program owner: [bio]
- Founding apprentice: [bio — populated after hire]
- AI agents: link to a sub-page describing the eight (this is a unique differentiator; lean into it)

### 9. Apply

Either embed the application form or link to it. Soft cap on application length.

### 10. Footer

- Built on Full Potential AI
- Manifesto link
- Privacy / data handling for applicants
- Contact email

## Visual direction

- Clean, slightly editorial, not "startup-y."
- Dominant typography over imagery.
- One photo or illustration max in hero. Keep visual noise down.
- Dark mode default; high contrast.
- Mobile-first.

## Tech stack suggestion

- Static site, Astro or Next.js (matches existing FPAI frontend stack).
- Hosted on Vercel or Cloudflare Pages.
- Form submissions go to a small endpoint in `apprentice-studio` that writes to `STATE/COHORT_1.json` (Recruiter agent picks up from there).
- Build pipeline: Recruiter agent generates the cohort 1 page content from `COHORT_1.json` so the site auto-updates as state changes.

## What goes live in v0 (Day 30)

- Hero
- What it is
- 10-week shape
- Manifesto link
- Founding apprentice section ("Meet the founding apprentice — [name + bio]")
- Email signup ("Get notified when cohort 1 applications open")

## What goes live in v1 (Day 60)

- Add cohort 1 section with tracks + dates
- Add application form
- Add three lenses + selection process

## What goes live in v2 (Day 200, post demo day)

- Add shipped products gallery
- Add alumni profiles
- Add demo day livestream replay
- Add "apply to cohort 2" prompt
