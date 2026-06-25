# brevo Mastery Card

## What it does best
Brevo is best for transactional email, contact-list email, and campaign-style sends when sender identity, consent, deliverability, and suppression handling are treated as first-class state.

## Optimal use patterns (concrete, with examples)
- Use verified sender domains and aligned from-addresses. Example: send product mail from a domain/subdomain configured for SPF, DKIM, and DMARC.
- Separate transactional mail from marketing flows. Transactional confirmations should not inherit campaign unsubscribe or throttling assumptions without intent.
- Respect consent and suppression state before every send. Import contacts with source/proof, not as anonymous rows.
- Keep templates small, clear, and consistent with the sender identity. Include plain-text fallback for important mail.
- Track bounce, complaint, unsubscribe, and delivered/open/click evidence back into local ops or CRM state.

## Anti-patterns (what silently degrades it)
- Sending from unverified or mismatched domains.
- Mixing cold outreach, marketing, and transactional messages in one reputation pool.
- Importing unconsented contacts or ignoring suppression lists.
- Large image-heavy messages with vague sender identity.
- Retrying hard bounces or complaints.

## Effort/parameter settings for this system
Default to review-only drafts unless James has explicitly approved a send. Use small batches, clear sender identity, and ledger every live send attempt with audience, source, and result.

## Key constraints and hard limits
Public outreach and live sends are James-gated. Codex may build templates, queues, checks, and reports, but must not send mail or change production sender settings without explicit approval.

## How to detect it's not performing well
Bounce/complaint rates rise, messages land in spam, from-address/domain alignment fails, unsubscribe handling is unclear, or the system cannot explain who received a message and why.

## Last updated + source
Seeded 2026-06-16 from Brevo deliverability patterns and FPAI public-send boundaries.

