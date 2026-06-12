"""
48-hour build challenge — brief generation + grading.

The brief is the same for every candidate at this stage (fairness). The grade
is per-submission, scored against an explicit rubric.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .stages import Candidate, Stage

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class ChallengeGrade:
    score: float                           # 0-1
    rationale: str
    sub_scores: dict[str, float] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)


GRADE_WEIGHTS = {
    "ships_and_runs": 0.30,    # the thing actually deployed and works
    "ai_collaboration": 0.25,  # uses AI as a collaborator, not a copy-paste oracle
    "code_quality": 0.20,      # readable, tested, defensive
    "system_thinking": 0.15,   # design choices reflect understanding of trade-offs
    "reflection": 0.10,        # the writeup shows learning, not just doing
}


def generate_brief(
    candidate: Candidate,
    deadline: Optional[datetime] = None,
    program_owner_email: str = "[owner-email]",
) -> str:
    """Generate the 48-hour challenge brief for a specific candidate."""
    if deadline is None:
        deadline = datetime.now() + timedelta(hours=48)

    deadline_str = deadline.strftime("%A, %B %d at %I:%M %p %Z").strip()

    return f"""# 48-Hour Build Challenge — Apprentice Studio

Hi {candidate.name.split()[0] if candidate.name else 'there'},

Thanks for advancing to Stage 2. This is a 48-hour build challenge — fixed for every Stage 2 applicant for fairness.

## Deadline

**{deadline_str}** (~48 hours from this message). If something genuinely blocks you and you need a small extension, write back. We do not penalise for asking.

## The Brief

Build and deploy a small AI service with the following shape:

> Take a piece of free-form input (text, URL, file, image — your choice).
> Produce something *useful* the user couldn't easily get without AI.
> Make it live and accessible at a public URL.

That's it. The rest is your call.

The point is not the cleverness of the idea. It's the shape of how you build with AI in the room.

## Constraints

- **Deployed.** A live URL we can hit. Localhost doesn't count.
- **Public-source friendly.** Code in a repo we can read (GitHub or similar).
- **Solo.** Your own work. AI assistants are encouraged — they're the point.
- **No frameworks of frameworks.** Keep it minimal. We want to see *your* choices, not Vercel's defaults.
- **Time-boxed.** Stop at 48 hours, even if unfinished. Better a small thing that runs than a big thing that doesn't.

## Deliverables

1. **The deployed URL.**
2. **The repo URL** with a short README that explains what it does and how to run it locally.
3. **A reflection** (max 500 words) titled `REFLECTION.md` in the repo root, answering:
   - What was the hardest moment, and how did you move through it?
   - Where was AI most useful as a *collaborator* (not just a code generator)?
   - What would you build next if you had another 48 hours?
   - What did you cut, and why?

## How we grade

Sum of weighted scores (each 0-1):

| Criterion | Weight | What we look for |
|---|---|---|
| Ships and runs | 30% | The deployed URL works on first hit. No "it works on my machine" excuses. |
| AI collaboration | 25% | The reflection shows AI was a real partner — you steered it; it didn't steer you. |
| Code quality | 20% | Readable, defensively written, has *some* tests. We don't expect production polish. |
| System thinking | 15% | Your choices show you understand trade-offs (cost, latency, failure modes). |
| Reflection | 10% | The writeup shows learning. We learn more about you from this than from the code. |

## What we're not grading

- Visual design polish.
- Cleverness of concept.
- Whether you finished everything you wanted to.
- Whether you used the same stack we do.

## Submitting

Reply to this email with:
1. Deployed URL
2. Repo URL
3. One sentence on what to look at first

We confirm receipt within 24 hours. Stage 3 (final conversation) decisions go out within 7 days of the deadline.

If you decide to withdraw from the challenge, just reply with "I'm withdrawing." That's a perfectly fine thing to do — we'd rather know than wait.

Good luck. Have fun.

—
The Apprentice Studio
{program_owner_email}
"""


def grade(
    candidate: Candidate,
    deployed_url_works: bool,
    code_quality: float,
    ai_collaboration: float,
    system_thinking: float,
    reflection_quality: float,
    notes: str = "",
) -> ChallengeGrade:
    """Grade a submission. All sub-scores 0-1.

    deployed_url_works is binary at the rubric level (ships_and_runs = 1.0 if
    True, else 0.0) because the rule is "either it ships or it doesn't."
    """
    sub = {
        "ships_and_runs": 1.0 if deployed_url_works else 0.0,
        "ai_collaboration": _clamp(ai_collaboration),
        "code_quality": _clamp(code_quality),
        "system_thinking": _clamp(system_thinking),
        "reflection": _clamp(reflection_quality),
    }
    score = sum(sub[k] * GRADE_WEIGHTS[k] for k in GRADE_WEIGHTS)

    strengths = [k.replace("_", " ").title() for k, v in sub.items() if v >= 0.8]
    concerns = [k.replace("_", " ").title() for k, v in sub.items() if v <= 0.3]

    if not deployed_url_works:
        concerns.insert(0, "Submission did not deploy")

    rationale_parts = [f"{k}: {v:.2f}" for k, v in sub.items()]
    if notes:
        rationale_parts.append(f"notes: {notes}")
    rationale = " | ".join(rationale_parts)

    candidate.challenge_score = round(score, 3)
    candidate.challenge_rationale = rationale
    if candidate.stage == Stage.CHALLENGE_SENT:
        candidate.transition(
            Stage.CHALLENGE_GRADED, by="challenge_grader",
            note=f"Challenge score: {score:.2f}"
        )

    return ChallengeGrade(
        score=round(score, 3),
        rationale=rationale,
        sub_scores={k: round(v, 3) for k, v in sub.items()},
        strengths=strengths,
        concerns=concerns,
    )


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))
