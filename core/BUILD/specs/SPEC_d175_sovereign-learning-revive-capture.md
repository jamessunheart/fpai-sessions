# SPEC d175 — Sovereign learning: revive the training-signal capture (rung 3 prerequisite)

**Why:** James — "we don't want to be too dependent on commercial models." Live audit 2026-07-04: sovereign INFERENCE exists (9 local ollama models; brain search on nomic-embed; bot fallback on llama), but no model LEARNS from the brain. The `brain_index.corrections` table (genesis 2026-06-15, the training signal for a self-evolving open model) has only **7 rows total** — capture is effectively dead. No fine-tune pipeline exists. Without signal, sovereign learning can never happen. This spec restarts the signal; the fine-tune itself is a later, separate spec.

## Build
1. **Diagnose why capture flatlined.** `corrections` schema = (conversation_id, bot_turn_id, original_response, james_correction, captured_at). Only 7 rows since 2026-06-15. Find the capture path: (a) the TG-side corrections capture in `curator/tgbot.py` (does a James reply that contradicts a bot turn get logged as a correction?), (b) the Claude-Code corrections hook (d125 — was it ever installed on the laptop? `~/.config/fpai/corrections/` is EMPTY). Report which capture points are dead vs alive.
2. **Revive both capture points.** TG: when James's message corrects/negates the bot's prior turn (heuristic + cheap classifier), write a corrections row. Claude Code: install the corrections-capture hook on the laptop (`.claude/hooks/`) so every "no, actually…" from James in the terminal becomes a training pair. Every correction = one (context, wrong, right) triple — the gold for fine-tuning.
3. **Also capture the merge-outcome signal** (already partly there): decisions + James's "merge dNNN good/meh" tags = preference pairs. Confirm they're queryable as training data.
4. **Measure, don't train yet.** Add a `fpos-health` line: corrections captured last 7d, total training pairs available. When the corpus crosses a threshold (e.g. 500 pairs), THAT triggers the fine-tune spec — not before (no point training on 7 examples).

## Contract
$0 · reversible (hooks + rows) · no fine-tune in this spec (measurement + signal-revival only) · independent review.

## Done / Proof
Corrections rows climb (a real James correction in TG or terminal lands within 1 min) · `~/.config/fpai/corrections/` fills from the terminal hook · fpos-health shows the 7d capture count + total-pairs · a documented "why it was dead" root cause in BUG_LOG.

## Sequenced-after (separate specs, not now)
- d0XX: benchmark qwen2.5/llama-70b vs Sonnet on our real tasks (spec d056 exists — run it) = sovereign QUALITY candidate.
- d0XX: the actual LoRA fine-tune on the corpus, once ≥500 pairs = sovereign LEARNING.
