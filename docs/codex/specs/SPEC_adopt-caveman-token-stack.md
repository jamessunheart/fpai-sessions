# SPEC_adopt-caveman-token-stack

*Scout + eval (NOT a commitment): assess the Caveman token-compression ecosystem (getcaveman.dev, MIT/open-source) for fit with FPOS. Evaluate the pieces that slot UNDER the existing stack — Cavemem (compressed cross-agent MCP memory) + the Caveman compression primitive (skill) — and explicitly DEFER the flagship Caveman Code CLI (it competes with the locked Claude Code + Codex workflow). Owner: Codex. Research + recommendation only.*

## Intent
James (2026-06-09): *"There's an app that uses less tokens and helps optimize — checkout getcaveman.dev."* It's a four-part open-source stack: **Caveman** (~75% model-agnostic compression skill) · **Cavemem** (persistent cross-agent memory, SQLite+FTS5+vector, via MCP, stored compressed) · **Cavekit** (spec→tasks) · **Caveman Code** (CLI, claims ~77% token savings, 20+ providers). It mirrors what FPOS hand-built (Cavemem≈sunheart-brain MCP · Cavekit≈the spec shop). On flat-rate plans it doesn't cut the bill — it buys headroom (effective context, rate-limit slack, speed). Decide what (if anything) is worth adopting.

## Routing
- Owner: **Codex** (research + write-up). Branch: `feat/scout-caveman`.
- Autonomy: 🟢 read-only — recommendation doc ONLY. 🔴 NO install of the CLI as a driver, NO swapping the locked workflow, NO money, NO secrets. Adopting any piece = a separate James-gated spec.
- Not urgent: must NOT preempt `feat/results-engine` or the human-edge chain. Background scout (sibling to `feat/scout-nemoclaw`).

## Definition of Done
A written eval — `docs/codex/scout/CAVEMAN_FIT.md` — answering concretely:
1. **The honest savings claim:** is the ~75–77% compression **lossy**? On what content? What's the fidelity cost (does it drop nuance that causes re-work)? Find independent evidence / benchmarks, not just the marketing page.
2. **Cavemem vs sunheart-brain:** does Cavemem's compressed MCP memory beat / complement / duplicate the existing brain MCP? Could we adopt its compression *under* the brain rather than replace it?
3. **Caveman compression primitive as a skill:** could the ~75% compression run as an MCP skill upstream of Claude Code / Codex *without* adopting the CLI — capturing the headroom while keeping the locked workflow? How?
4. **Explicit DEFER on Caveman Code CLI:** state why (OPERATING WORKFLOW already locked Claude Code + Codex; a third driver fragments the loop). Note the trigger that would reopen it.
5. **Recommendation per piece:** `adopt now` / `adopt when [trigger]` / `park` — for Cavemem, the compression primitive, Cavekit, and the CLI separately. Flag any license/security caveats (MIT confirm · supply-chain of the npm/MCP packages).

- Files ALLOWED: `docs/codex/scout/CAVEMAN_FIT.md` (new) · read-only web/GitHub research. Files FORBIDDEN: installing/running the CLI as a driver · touching the live workflow/brain · money · secrets · npm installs into the repo.
- Tests: n/a (research) — DoD is the doc answering all 5 with sources.

## Close-out
HANDOFF 📥 + a one-line World Scout candidate entry per piece. If a piece scores `adopt`, James reviews before any adopt spec is written. BRICK the fit-eval method if reusable.
