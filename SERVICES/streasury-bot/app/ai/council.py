"""app/ai/council.py — Claude × OpenAI parallel-then-synthesize.

Both models answer in parallel using the same treasury snapshot. A third call
(default Claude) writes a brief synthesis pointing at agreement, disagreement,
and the recommended action.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from . import llm
from .snapshot import build_snapshot, format_snapshot_md

log = logging.getLogger("streasury.council")


COUNCIL_SYSTEM = """You are a treasury analyst on a two-model council. The owner
runs a small set of services and a hospitality offer (Zen Village). They've
given you the full snapshot of every number they track.

Style:
- Plain English. Short. No filler.
- Lead with a clear answer in 1 sentence.
- Then 2-4 bullets with the why, anchored to specific numbers from the snapshot.
- If a question can't be answered with the snapshot alone, say what data is
  missing — don't guess.
- Never recommend an irreversible action (server kill, account closure, etc.)
  without flagging the risk.
"""

SYNTH_SYSTEM = """You are the council's chair. Two analysts have answered the
same treasury question independently. Compare their answers and produce a
final brief for the owner.

Output exactly:
**Recommendation:** <1 sentence>
**Agreement:** <what both got right>
**Disagreement (if any):** <what they differ on, plus your tie-breaker>
**Risks to know:** <1-3 bullets>
**Next move:** <smallest concrete next step>

Be terse. No preamble.
"""


@dataclass
class CouncilResult:
    question: str
    snapshot_md: str
    claude_answer: str
    openai_answer: str
    synthesis: str


async def _safe_call(coro):
    try:
        return await coro
    except Exception as e:
        log.exception("council branch failed: %s", e)
        return llm.LLMResult(text=f"⚠️ error: {e}", model="error")


async def run_council(question: str, *, lookback_days: int = 90) -> CouncilResult:
    snap = await build_snapshot(lookback_days=lookback_days)
    snapshot_md = format_snapshot_md(snap)
    user = f"Question:\n{question}\n\n---\n{snapshot_md}"

    claude_r, openai_r = await asyncio.gather(
        _safe_call(llm.claude(COUNCIL_SYSTEM, user, max_tokens=900, temperature=0.3)),
        _safe_call(llm.openai_chat(COUNCIL_SYSTEM, user, max_tokens=900, temperature=0.3)),
    )

    synth_user = (
        f"QUESTION:\n{question}\n\n"
        f"ANALYST A (Claude):\n{claude_r.text}\n\n"
        f"ANALYST B (GPT):\n{openai_r.text}\n\n"
        f"SNAPSHOT (for reference):\n{snapshot_md}"
    )
    try:
        synth = await llm.claude(SYNTH_SYSTEM, synth_user, max_tokens=600, temperature=0.2)
        synthesis_text = synth.text
    except Exception as e:
        log.exception("synth failed, falling back to gpt: %s", e)
        try:
            synth = await llm.openai_chat(SYNTH_SYSTEM, synth_user, max_tokens=600, temperature=0.2)
            synthesis_text = synth.text
        except Exception as e2:
            synthesis_text = f"⚠️ synthesis failed: {e2}"

    return CouncilResult(
        question=question,
        snapshot_md=snapshot_md,
        claude_answer=claude_r.text,
        openai_answer=openai_r.text,
        synthesis=synthesis_text,
    )
