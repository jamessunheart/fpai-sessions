# SPEC_adopt-nemoclaw-local-agents

*Scout + eval (NOT a commitment to deploy): assess NVIDIA's no-subscription local-agent stack — NemoClaw blueprint (open models + OpenClaw/Hermes harness + OpenShell runtime) + Nemotron 3 open weights — for fit with FPOS's cost-optimized autonomy ladder. Owner: Codex. Read-only research + a written recommendation. Decision to actually adopt/deploy stays James's.*

## Intent
James (2026-06-09): *"Review the latest NVIDIA AI that requires no subscription — does it fit our system? Scout it."* NVIDIA shipped (June 2026) a free, open, no-subscription stack: **NemoClaw** (run autonomous agents on hardware you own, zero per-token cost, context stays on-device) + **Nemotron 3** open-weight models (Nano 4B on RTX → Ultra 550B). The cockpit already named **OpenClaw "the leading adopt-not-build candidate."** This eval confirms whether it earns a place in the stack — or stays parked.

## Routing
- Owner: **Codex** (research + write-up). Branch: `feat/scout-nemoclaw`.
- Autonomy: 🟢 read-only — produces a recommendation doc ONLY. 🔴 NO install, NO deploy, NO hardware purchase, NO money — adopting is a separate James-gated spec if this eval says go.
- Not urgent: must NOT preempt `feat/results-engine` or the human-edge chain. Background scout.

## Definition of Done
A written eval — `docs/codex/scout/NEMOCLAW_FIT.md` — answering, concretely:
1. **What it is, current (June 2026):** NemoClaw blueprint components · Nemotron 3 tiers (Nano 4B / Super 120B / Ultra 550B) + their hardware floors · OpenClaw/Hermes agent harness · license terms (confirm genuinely no-subscription + commercial-use-ok).
2. **The honest cost delta:** FPOS already runs ~$0 marginal on Claude Max + Codex (GPT Pro) flat-rate. So what does local NVIDIA actually *add*? (independence from cloud subs · privacy / on-device sensitive context · owned-hardware always-on autonomy · the "SSH/Build Host" James circled). Name what it does NOT add (it doesn't cut today's bill).
3. **Hardware gate:** what's the minimum box to run a *useful* agent locally (RTX tier vs DGX Spark) · rough $ · does James already have anything that qualifies (he answers).
4. **Fit verdict vs doctrine:** map against "flat-rate first · adopt not build · don't add for hypothetical demand (G4) · read-only/secrets-safe." Score it like a World Scout candidate.
5. **Recommendation:** one of — `adopt now (draft deploy spec)` · `adopt when [trigger]` · `park as logged candidate`. With the trigger named (e.g. "when we want the autonomous loop off cloud / on owned hardware / handling sensitive data").

- Files ALLOWED: `docs/codex/scout/NEMOCLAW_FIT.md` (new) · read-only web research. Files FORBIDDEN: any install/runtime/deploy · hardware/money · secrets · touching the live loop.
- Tests: n/a (research doc) — DoD is the doc answering all 5 sections with sources.

## Close-out
HANDOFF 📥 + a one-line World Scout candidate entry. If verdict = adopt, James reviews before any deploy spec is written. BRICK the fit-eval method if reusable.
