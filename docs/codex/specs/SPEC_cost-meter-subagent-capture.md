# SPEC · Cost meter — subagent token capture

## Source
- From intent: SI-1 follow-up — the live meter's known gap (the-forge flagged): Task **subagent** tokens write to separate transcripts and aren't auto-captured, so big fan-outs undercount.
- Why it matters: makes the $20/day meter trustworthy for agent-heavy turns, not just the main loop.

## Routing
- Owner / route: **Codex** (small, local).
- Autonomy tier: 🟢 auto-build eligible (local script edit, reversible, no external).
- Tools: repo edit only.

## Cost
- Est: ⚡ <$0.50. Gate: 🤖 auto-build (cheap · reversible · local).

## Codex
- Branch: `fix/cost-meter-subagent-capture`
- Files ALLOWED: `.claude/hooks/cost-tally.sh`, `~/.local/bin/cost-log`, `~/.config/fpai/cost/**`
- Files FORBIDDEN: anything else
- Budget: <$0.50
- Tests: spawn a Task subagent, confirm its tokens land in `~/.config/fpai/cost/ledger.jsonl`; `cost-today` total includes them; idempotent (no double-count)
- Parallel-safe: yes (cost files only)

## The work
- Definition of done: subagent/Task transcripts are discovered + their token usage summed into the cost ledger (idempotent via a cursor), so `cost-today` reflects fan-out cost. Update [[COST LEDGER]] limitation note when fixed.
- Steps: 1) locate subagent transcript dir 2) parse usage 3) merge into ledger with dedup cursor 4) test fan-out 5) update the COST LEDGER honest-limit note.
- Constraints: reversible (script edits); fail-open (never break the Stop hook).

## Safety
- Rollback: revert cost-tally.sh; ledger is append-only + idempotent.

## Close-out
- Eval · actual cost · proof → [[PROOF LOG]] · BRICK.
