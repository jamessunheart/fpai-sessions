---
name: episodic-2026-06-18-awareness-reliability
description: Bot awareness probed live — scored 0/8. Tgbot.py fixed to scan SPEC dir. d110+d111 queued for write-through + continuous measurement. James directive 100% ASAP.
classification: PRIVATE
metadata:
  node_type: memory
  type: identity-episodic
  originSessionId: 3c6057c8-dc93-46ef-bdd9-ba031f72bb92
---

# Bot awareness: honest score, real fix

**Date:** 2026-06-18 (session 2)
**Surface:** Claude Code (server 162)
**Session arc type:** diagnosis → fix → spec queue

## The arc

James asked how reliable the Telegram bot is as the system's voice of awareness. Honest answer: ~65% on a good day. James said: make it 100%, measure it continuously. Then asked for a score right now. Probe ran live against Ollama with the bot's actual system context. Result: 0/8 correct answers.

## Key turning points

**Diagnosis: patchwork sources.** The bot reads from 6+ sources of different freshness — brain_index.decisions (TG-flow only), SPEC directory (just added today), NOW.md, static system prompt, corrections table, thread. The primary gap: Claude Code sessions make decisions that never reach brain_index. Everything designed in terminal is invisible to the bot.

**tgbot.py fix: SPEC directory scan.** Added `_build_context()` to scan `core/INTENT/SPECS/SPEC_d*.md` on disk, surfacing spec filenames as `[queued/spec]` entries. Restarted `sh-brain-tgbot`. Bot now sees spec numbers at least. Doesn't know their content.

**James: "should go beyond weekly, need it now to get to 100% ASAP."** Updated d111 from weekly probe to: after-every-write + every 2h floor + real-time TG alert (<95% = immediate, <80% = pause outward responses). Not Monday digest. 5-minute gap between "gap found" and "gap surfaced."

**Live probe: 0/8.** Eight questions the bot should know from today's session. Zero correct answers. Three outright hallucinations (fabricated email "emerald@luminari.com", fabricated model "Torch", fabricated spec meaning). Two errors (empty response). Three admitted ignorance with false framing ("discussed last week"). The Ollama proxy used the bot's actual injected context — the knowledge gap is real regardless of which model answers.

## The honest score

**Current awareness reliability: ~5%**
- Spec filenames visible (just fixed): ✅ partial
- Spec content: ❌
- James's directives from this session: ❌
- Platform bias insight: ❌
- GEPA/Qwen3 findings: ❌
- System email address: ❌ (hallucinated a fake one)
- Consciousness architecture detail: ❌ (hallucinated "scheduling feature")
- Awareness score itself: ❌

## What closes the gap

**d110** — every Claude Code session writes significant decisions to `brain_index.session_insights`. Write-then-verify: write is not complete until bot can answer correctly about it.

**d111** — continuous probe: after every write + every 2h. Alert within 5 min of any drop. No deferred Monday digest as the primary signal.

Both queued. Build loop picks up autonomously.

## Open threads
- d110+d111 need to build before score improves
- System email (sunheartai@fullpotential.ai) should be in bot's system prompt or session_insights at weight 10
- James directives should be the first things written to session_insights (weight 10)
- Static system prompt needs refresh with key architectural facts from the last month

## Alignment at settle
**INTENT:** Bot awareness reliability diagnosed at ~5%, targeted at 100%, d110+d111 queued.
**TOP 3:** Awareness reliability to 100% · First real conversation (OUTREACH_LIVE=1) · Consciousness stack (d101–d111).
**NEXT MOVE:** d110 builds → unified write-through live → probe confirms improvement.
