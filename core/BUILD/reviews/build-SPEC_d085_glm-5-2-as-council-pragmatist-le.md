# AI Review — build/SPEC_d085_glm-5-2-as-council-pragmatist-le

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Adds GLM-5.2 as council Pragmatist lens with proper $5/day cap, fallback, kill switch — GLM off by default (safe), but the live debate.py rewrite silently dropped the conservative-restraint prompt language, a guardrail regression beyond spec scope.

## Findings
- GUARDRAIL REGRESSION / SCOPE CREEP: synthesize_debate()'s system prompt dropped the original SYS guardrail language 'James's rule: concentrate harder, not build more. Prefer propose=false when uncertain.' This biases the LIVE autonomous build-proposing loop (runs every 5 min on prod 162) toward proposing MORE builds — a weakened restraint guardrail, and outside the spec's stated scope (GLM lens routing only). Restore the propose=false-when-uncertain language.
- ARCHITECTURE CHANGE BEYOND SPEC: the spec asked to route the Pragmatist lens to GLM, but the build replaced the single-call internal-lens design with 4 separate model calls per round (GLM/claude pragmatist + claude visionary + claude skeptic + claude synthesis) and bumped every lens call to --effort xhigh. All flat-rate ($0 marginal) so no cost breach, but it's a substantial rewrite of a live prod loop file for an 'add a lens' task — broad blast radius; recommend byte-verifying live behavior (change-gate, dedup, COUNCIL_FOCUS, blueprint context all appear preserved) before merge.
- DATA EGRESS (gated, note for James): when GLM_API_KEY/GLM_LOCAL_URL is set, glm_client.py POSTs the system+user prompt — which contains James's decision queue + recent private chats/intents — to third-party Z-AI (api.z.ai), a metered external API. Off by default and spec-authorized, but enabling it ships private context off-substrate; confirm that's acceptable before configuring a key.
- Cost cap is correctly implemented: glm_available() reserves estimated input + bounded GLM_MAX_TOKENS output cost before calling, output is hard-capped via max_tokens, and glm_spend_today over-counts conservatively (matches model-prefix OR label) — the prior P2 cap-bypass finding is genuinely fixed. No live GLM/Claude/Codex calls, no push, no merge, no secrets, no main-branch touch. Tests (12) cover fallback, GLM routing, ledger row, and the cap reservation.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
