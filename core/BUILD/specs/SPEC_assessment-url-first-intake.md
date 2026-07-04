# SPEC — URL-first Assessment intake (the magic onboarding upgrade)

Highest experience-lift idea for the flagship Assessment (vault: The Great Assessment — Experience Design). Turn 15 min of typing into ~5 min + a live demonstration of intelligence.

## Build
On /assessment: add a "Your website (optional but magic)" field. On submit with a URL:
1. web-fetch the public site (home, about, pricing, services pages) — read-only, respect robots.
2. Pre-populate the intake: business type, apparent tools/stack, team signals, pricing model, ops hints → feed as pre-filled context to `tools/growth/score_assessment.py`.
3. Show an instant "our first read" panel ("Here's what we already see about how you allocate…") BEFORE they finish — the wow moment. They confirm/correct, then get the full Score.
Backend: extend score_assessment with a `--url` path that fetches + summarizes the site into the intake. $0 (web-fetch + claude -p). Guardrails: read-only, no login-walled pages, timeout, cache per-domain.

## Done / Proof
Enter a real business URL → instant accurate first-read + pre-filled intake → full Score. Cuts typed input ~60%.
