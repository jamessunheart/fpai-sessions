#!/usr/bin/env python3
"""Map-surveyor conversation engine (MTUE/HIL-native).

NOT a rigid 6-field form. Each turn the MODEL decides: do I have enough of this
person's map to give a genuinely useful Allocation Score, or what is the single
best next question? When ready, it calls the proven score_assessment scorer.
Exercisable end-to-end: --selftest runs a simulated persona conversation.
"""
from __future__ import annotations
import json, sys, argparse
from tools.growth.score_assessment import run_claude, score_one

SURVEY_PROMPT = """You are surveying a business owner's "map" for a free Full Potential Assessment,
under one law: respect their time — ask the FEWEST questions that let you give a genuinely useful
Allocation Score (how well they allocate capital, time, attention, people, AI, knowledge).

Conversation so far:
{transcript}

If you already have enough to give a useful, specific score (you understand what the business is,
its rough size, and the main place value is leaking), return:
{{"ready": true}}

Otherwise return:
{{"ready": false, "next_question": "<the single best next question, warm and conversational, in Ember's voice — never a form field, always a real question that a sharp advisor would ask next>"}}

Ask at most 3-4 questions total across the whole conversation. When in doubt, lean toward ready —
a great 2-question assessment beats an annoying 6-question one. Return ONLY JSON."""

PERSONA_PROMPT = """You are role-playing a real business owner in a chat. Stay in character, answer
naturally and briefly (1-2 sentences), like texting. Don't volunteer everything at once.

Your character:
{persona}

Conversation so far:
{transcript}

The assistant just said: "{question}"
Reply as the owner. Return ONLY your reply text, no quotes."""


def survey_turn(transcript: str) -> dict:
    return run_claude(SURVEY_PROMPT.format(transcript=transcript))


def render_transcript(turns: list[tuple[str, str]]) -> str:
    return "\n".join(f"{'Owner' if r=='user' else 'Ember'}: {t}" for r, t in turns)


def selftest(persona: str, opener: str, max_turns: int = 6):
    turns: list[tuple[str, str]] = [("assistant", opener)]
    print(f"Ember: {opener}")
    for i in range(max_turns):
        # persona replies
        reply = run_claude_text(PERSONA_PROMPT.format(
            persona=persona, transcript=render_transcript(turns), question=turns[-1][1]))
        turns.append(("user", reply))
        print(f"Owner: {reply}")
        # surveyor decides
        decision = survey_turn(render_transcript(turns))
        if decision.get("ready"):
            print("\n--- SURVEYOR: enough map. Scoring. ---\n")
            deliverable = score_one(render_transcript(turns))
            print(deliverable[:1600])
            return {"turns": len(turns), "scored": True}
        q = decision.get("next_question", "Tell me a bit more?")
        turns.append(("assistant", q))
        print(f"Ember: {q}")
    return {"turns": len(turns), "scored": False}


def run_claude_text(prompt: str) -> str:
    # persona replies are plain text, not JSON — reuse the CLI path loosely
    from tools.growth.score_assessment import _run_claude_cli
    try:
        return _run_claude_cli(prompt).strip().strip('"')
    except Exception:
        # fall back to router JSON path wrapping
        try:
            d = run_claude('Return {"t":"..."} with your reply as t. ' + prompt)
            return str(d.get("t", "")).strip()
        except Exception as e:
            return f"(persona error: {e})"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        persona = ("Owns a 2-location pilates studio, 12 instructors. Front desk hand-copies "
                   "Mindbody data into a Google sheet. Pays for an AI tool nobody uses. Wants a "
                   "third location but scared it'll break her. Warm, busy, slightly overwhelmed.")
        opener = "Hi — I'm James Sunheart + AI. Tell me what you're building, in a sentence or two."
        print(json.dumps(selftest(persona, opener)))
