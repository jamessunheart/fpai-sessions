"""
Interview prep — generate a dossier for the human before each Stage 3 conversation.

The dossier is the briefing the human reads in 5 minutes before the call. It
should compress everything we know into: who, what to look for, what to ask,
red flags, and a recommended decision frame.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .stages import Candidate


def dossier(candidate: Candidate, founding_apprentice_name: Optional[str] = None) -> str:
    """Produce a Markdown dossier for the human pre-interview."""
    name = candidate.name or "(no name)"
    score_screen = candidate.screening_score
    score_chal = candidate.challenge_score
    overall = _overall(score_screen, score_chal)

    lines: list[str] = []
    lines.append(f"# Interview Dossier — {name}")
    lines.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")
    lines.append(f"**Email:** {candidate.email}")
    lines.append(f"**Source:** {candidate.source}")
    lines.append(f"**Stage:** {candidate.stage.value}")
    lines.append("")

    lines.append("## Scores")
    lines.append(f"- Screening: **{_fmt(score_screen)}**  ({candidate.screening_rationale or '—'})")
    lines.append(f"- Challenge: **{_fmt(score_chal)}**  ({candidate.challenge_rationale or '—'})")
    lines.append(f"- Overall (so far): **{_fmt(overall)}**")
    lines.append("")

    if candidate.strengths:
        lines.append("## Strengths")
        lines.extend(f"- {s}" for s in candidate.strengths)
        lines.append("")

    if candidate.concerns:
        lines.append("## Concerns")
        lines.extend(f"- {c}" for c in candidate.concerns)
        lines.append("")

    if candidate.flags:
        lines.append("## Flags")
        lines.extend(f"- {f}" for f in candidate.flags)
        lines.append("")

    app = candidate.application
    if app:
        lines.append("## Their Words")
        for k in [
            "what_to_build", "lens_fit", "why_this",
            "ai_collaborator_story", "ai_workflow", "shipped_thing",
        ]:
            v = app.get(k)
            if v:
                title = k.replace("_", " ").title()
                lines.append(f"### {title}")
                lines.append(str(v).strip())
                lines.append("")

    lines.append("## What to listen for in this call")
    lines.append("Pick 3-5 of these to actually ask. The rest are optional.")
    lines.append("")
    lines.extend([
        "- **Ownership** — when did you last quit on something, and why?",
        "- **AI as collaborator** — walk me through the last 30 minutes you used Claude/Cursor. What was the loop?",
        "- **Three lenses** — how does what you want to build hit regenerative / sovereignty / consciousness? Which lens do you actually care about?",
        "- **Ship rhythm** — what's the smallest useful version of your idea you could ship in 7 days?",
        "- **Failure mode** — what's the way you'd most likely fail in this program?",
        "- **Money** — are you OK that this isn't a salary? Why?",
        "- **Group fit** — when has being on a team made you better, and when has it made you worse?",
        "- **The hard ask** — what's something you'd want from this program that we haven't promised?",
    ])
    lines.append("")

    if founding_apprentice_name:
        lines.append("## What the founding apprentice should listen for")
        lines.append(f"({founding_apprentice_name} attends with you.)")
        lines.append("")
        lines.extend([
            "- **Code judgment** — would you actually want to ship next to this person?",
            "- **AI fluency** — is their AI workflow real or performative?",
            "- **Stuckness recovery** — when stuck, do they spiral or move?",
        ])
        lines.append("")

    lines.append("## Decision frame")
    lines.append(_decision_frame(overall, candidate))
    lines.append("")

    lines.append("## After the call — log here")
    lines.append("```")
    lines.append("Interview score (0-1):  ___")
    lines.append("Decision (advance / decline / hold):  ___")
    lines.append("One sentence on why:  ___")
    lines.append("```")
    lines.append("")
    lines.append(f"Then run: `python funnel.py interviewed {candidate.id} --score <0-1> --decision <advance|decline>`")

    return "\n".join(lines)


def log_interview(candidate: Candidate, score: float, note: str = "") -> None:
    """Record interview score on the candidate."""
    candidate.interview_score = round(_clamp(score), 3)
    candidate.interview_rationale = note


def _overall(screen: Optional[float], challenge: Optional[float]) -> Optional[float]:
    parts = [v for v in (screen, challenge) if v is not None]
    if not parts:
        return None
    return round(sum(parts) / len(parts), 3)


def _fmt(v: Optional[float]) -> str:
    return f"{v:.2f}" if v is not None else "—"


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _decision_frame(overall: Optional[float], candidate: Candidate) -> str:
    if overall is None:
        return "Insufficient data. Use the call to determine signal."
    if overall >= 0.85:
        return "**Strong default: advance.** This call is to find a reason *not* to."
    if overall >= 0.70:
        return "**Default: advance, but probe concerns.** Use this call to resolve specific concerns above."
    if overall >= 0.55:
        return "**Default: hold, unless the call shifts your read.** They're decent but not a clear yes."
    return "**Default: decline, unless the call surprises you.** The data so far doesn't pass the bar."
