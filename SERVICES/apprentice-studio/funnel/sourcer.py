"""
Outbound sourcer — track prospects + draft personalised outreach.

The sourcer doesn't actually find people (that's research the human or a search
agent does); it's the bookkeeping + drafting layer for outbound.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .stages import Candidate


def draft_outbound_message(
    candidate: Candidate,
    why_this_person: str,
    program_owner_name: str = "[Program Owner]",
) -> str:
    """Draft a personalised outbound message for a sourced prospect."""
    first = candidate.name.split()[0] if candidate.name else "there"
    return f"""# Outbound draft — {candidate.name}

**To:** {candidate.email}
**Subject:** A 90-day thing you might want to know about

---

{first},

Short note. We're starting a small AI-native studio inside Full Potential AI — 4 to 6 apprentices per cohort, building real products with AI as a co-builder. You came up because **{why_this_person}**.

Three things in case it's interesting:

1. **It's not a job.** Apprentices keep 70% equity in what they build. We provide infra, mentorship, AI tooling, housing during retreat weeks.
2. **It's selective.** We're hiring one founding apprentice first (60-90 days, paid), then opening a 4-6 person cohort.
3. **It's mission-shaped.** Tools that *expand* humans, not replace them. We screen for that explicitly.

If you want to know more, I'll send you the manifesto + founding-apprentice role. No expectation either way.

Reply if you're curious. Or ignore — no awkwardness.

—
{program_owner_name}

*p.s. — saw it in passing, but {why_this_person.lower()}. Genuinely.*
"""


def draft_followup_after_silence(
    candidate: Candidate,
    days_since_first: int,
    program_owner_name: str = "[Program Owner]",
) -> str:
    """A gentle follow-up if there's been silence."""
    first = candidate.name.split()[0] if candidate.name else "there"
    return f"""# Outbound follow-up — {candidate.name}

**To:** {candidate.email}
**Subject:** Re: A 90-day thing you might want to know about

---

{first},

Quick follow-up — totally fine if it's a no or not now. Just want to close the loop.

The founding apprentice spot is closing on **[DATE]**. After that we open the cohort 1 application instead.

If timing's wrong but you want to be considered for cohort 1, reply with anything and I'll add you to the early list.

If it's just a no, you can ignore this. No follow-ups after this.

—
{program_owner_name}
"""
