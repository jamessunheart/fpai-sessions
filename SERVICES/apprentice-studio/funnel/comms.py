"""
Generic comms drafts that don't fit elsewhere — advance/decline at each stage.

All drafts go to outbox/<candidate_id>/<filename>.md. Nothing sent.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .stages import Candidate, Stage


def draft_advance_to_challenge(
    candidate: Candidate,
    challenge_deadline: datetime,
    program_owner_name: str = "[Program Owner]",
) -> str:
    first = candidate.name.split()[0] if candidate.name else "there"
    return f"""# Advance to Stage 2 — {candidate.name}

**To:** {candidate.email}
**Subject:** Apprentice Studio — you're advancing to Stage 2

---

{first},

You're advancing to Stage 2 of the founding apprentice / cohort 1 selection process.

Stage 2 is a **48-hour build challenge**. The full brief is attached as `BUILD_CHALLENGE.md`.

**Deadline:** {challenge_deadline.strftime("%A, %B %d at %I:%M %p")} — about 48 hours from when you confirm receipt of this message.

To start, just reply with **"received"** and we'll consider the clock running from your reply timestamp. (If now isn't a good 48-hour window, tell us — we accept reasonable shifts.)

If you want to withdraw, no awkwardness — just reply "withdrawing."

—
{program_owner_name}
"""


def draft_decline(
    candidate: Candidate,
    stage: Stage,
    program_owner_name: str = "[Program Owner]",
) -> str:
    """A respectful, specific decline at any stage."""
    first = candidate.name.split()[0] if candidate.name else "there"
    stage_phrase = {
        Stage.SCREENED: "your application",
        Stage.CHALLENGE_GRADED: "your build submission",
        Stage.INTERVIEWED: "our conversation",
    }.get(stage, "your application")

    keep_on_file = "If you'd like us to keep you in mind for cohort 2, just reply 'keep'."

    return f"""# Decline — {candidate.name}

**To:** {candidate.email}
**Subject:** Apprentice Studio — update on your application

---

{first},

Thanks for {stage_phrase}. We're not going to advance you further this round.

A few honest notes (not feedback you have to act on, just signal):

- {_decline_signal_strength(candidate)}
- {_decline_signal_concern(candidate)}

Most applicants we declined are genuinely strong. The cohort is small and we're optimising for fit, not absolute quality. Take this as our constraint, not your verdict.

{keep_on_file}

—
{program_owner_name}
"""


def draft_advance_to_interview(
    candidate: Candidate,
    interview_window: str,
    program_owner_name: str = "[Program Owner]",
) -> str:
    first = candidate.name.split()[0] if candidate.name else "there"
    return f"""# Advance to Stage 3 — {candidate.name}

**To:** {candidate.email}
**Subject:** Apprentice Studio — Stage 3 conversation

---

{first},

Your build challenge submission landed. You're advancing to Stage 3 — a 60-minute conversation with me (program owner) and our founding apprentice if hired.

We have these windows open:

{interview_window}

Reply with your top two preferences. We'll confirm one within 24 hours.

What to expect:
- 60 minutes, video call.
- Half a conversation about what you'd build, half a conversation about what you care about.
- We will ask about your build challenge — be ready to walk through choices.
- It's OK to ask us anything back. The decision is mutual.

—
{program_owner_name}
"""


def _decline_signal_strength(candidate: Candidate) -> str:
    if candidate.strengths:
        return f"What stood out: **{candidate.strengths[0]}.** That part is real."
    return "Your willingness to apply is itself a signal — most people don't."


def _decline_signal_concern(candidate: Candidate) -> str:
    if candidate.concerns:
        return f"What we wanted more of: **{candidate.concerns[0].lower()}.** This is a fixable thing, not a verdict on you."
    return "Fit, not fundamentals — for this cohort specifically."
