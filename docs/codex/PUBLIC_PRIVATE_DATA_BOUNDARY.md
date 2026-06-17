# Public/Private Data Boundary

This is the builder-facing policy for keeping public-shareable material separate from personal, sensitive, legal, treasury, and operational context.

Canonical machine policy: `core/STATE/PUBLIC_PRIVATE_DATA_BOUNDARY.json`

Enforcement helper: `tools.public_private_boundary.boundary`

## Lanes

| Lane | Use | Routing |
|---|---|---|
| `public` | Approved public copy, public product language, aggregate proof, non-identifying lessons | May leave the private system only after validation passes |
| `internal` | Repo/buildstream IDs, branches, paths, test commands, service names | Keep internal; public output must summarize without raw IDs or paths |
| `private` | James state, location, schedule, relationships, legal/treasury/people strategy, private conversations | Private reasoning and handoff only; extract only non-identifying lessons |
| `sensitive` | Credentials, tokens, passwords, keys, seed phrases, session cookies, private identifiers | Never public; redact from logs/summaries and escalate suspected exposure |

## Mixed Conversation Rule

When a conversation contains both public-shareable content and personal/sensitive context, the system routes it as `split`.

- Public lane receives only sanitized fragments that classify as `public`.
- Private lane retains the full context for reasoning, handoff, and follow-up.
- If sanitized public text still matches `internal`, `private`, or `sensitive`, publication fails closed.

## Public Output Contract

Public-bound code should call `sanitize_public_text()`, `validate_public_text()`, `enforce_public_text()`, or `route_conversation()` instead of hand-rolling regex checks.

The visual digest public story feed now uses this boundary module before rendering and before sending.
