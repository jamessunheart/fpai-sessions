# Healer Policy — what the system may auto-fix (Decision d001, James 2026-06-14)

> Your call: **"yes to safe auto-fix policy."** Reversible, non-prod only. The
> *executor* (code that actually performs fixes) stays GATED behind a second go —
> this doc is the policy, not yet the actor.

## ✅ MAY auto-fix (reversible · non-prod · no approval needed)
- Restart a failed **non-prod** service
- Refresh a stale map / cache / index (e.g. SYSTEM_MAP rebuild)
- Retry a failed build (bounded retries)
- Re-run an idempotent local script that errored transiently

## 🔴 MUST NEVER touch (always requires James)
- **Money** — any treasury / trading / real-funds action (Reserved-Class)
- **Prod servers** — 162 · 198 · 209 (writes need explicit per-action "go")
- **Identity stack** — Ember's identity/memory files
- **`main` branch** — auto-work lands on feat branches only

## Guardrails (every auto-fix)
- Backup + rollback path before acting · small blast radius
- Log every auto-fix to a receipt (Proof Return)
- Stop + surface to James after N consecutive failures (no thrashing)

## Status
- Policy: **DECIDED** (this doc).
- Executor: **GATED** — building the actor that enforces this needs a separate explicit go.
