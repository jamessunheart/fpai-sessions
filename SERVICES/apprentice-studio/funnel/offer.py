"""
Offer + onboarding pack generator.

When a candidate has been INTERVIEWED with advance decision, we generate:
  - offer-letter.md   — short, plain language, terms clearly stated
  - contract.md       — slightly more formal terms (you take to a lawyer)
  - onboarding.md     — week-1 plan ready before they say yes
  - welcome-msg.md    — short personal note in James's voice
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .stages import Candidate


def generate_offer_letter(
    candidate: Candidate,
    role: str = "Founding Apprentice",
    compensation_usd: int = 35000,
    duration_days: int = 90,
    start_date: Optional[datetime] = None,
    program_owner_name: str = "[Program Owner]",
    program_owner_email: str = "[owner-email]",
) -> str:
    if start_date is None:
        start_date = datetime.now() + timedelta(days=10)

    end_date = start_date + timedelta(days=duration_days)

    return f"""# Offer — {role}

**To:** {candidate.name} <{candidate.email}>
**From:** {program_owner_name}, Apprentice Studio (Full Potential AI)
**Date:** {datetime.now().strftime("%B %d, %Y")}

---

{candidate.name.split()[0] if candidate.name else 'Hi'},

I'd like to offer you the **{role}** role at the Apprentice Studio.

## Terms

| | |
|---|---|
| **Role** | {role} |
| **Start date** | {start_date.strftime("%A, %B %d, %Y")} (negotiable within 7 days) |
| **Duration** | {duration_days} days, with conversion to **Studio Lead** at full-time comp on success |
| **Compensation** | ${compensation_usd:,} for the {duration_days}-day term, paid monthly |
| **Equity** | You retain 70% of any product you build under this engagement (per the studio's 70/20/10 split) |
| **Default license** | Anything built using FPAI infrastructure carries a default license back to FPAI for studio use |
| **Tools** | Unlimited Anthropic / OpenAI / Google API credits. Full FPAI infrastructure access. Your own Aria instance. |
| **Location** | Onsite for first 30 days (housing covered); hybrid afterwards |

## Primary deliverable

Ship **Apprentice OS v0.1** by Day 60. The toolkit every future apprentice will use to onboard, build, and demo inside FPAI.

Secondary contributions:
- Improve existing FPAI services where you spot leverage.
- Document the studio's operating model from the inside.
- Co-write the cohort 1 curriculum.
- Help recruit cohort 1.

## What we need from you

- Reply to confirm you'd like to accept by **{(datetime.now() + timedelta(days=7)).strftime("%A, %B %d")}** (7 days from today).
- If you want to negotiate any of the above, write back. We'd rather you ask than say yes to terms you don't actually want.
- A signed contract before Day 1. We'll send a draft within 48 hours of your acceptance.

## What you can expect from us

- A clear week-1 plan ready before you arrive (separate document attached).
- Your Aria instance provisioned and ready.
- Full repo access on Day 1.
- A 30-minute 1:1 with me on Day 1, and weekly afterwards.

This is a real role with real expectations. It is also designed to be one of the best 90 days you've spent. If you say yes, we'll make it that.

Looking forward to your reply.

—
{program_owner_name}
{program_owner_email}

---

*This offer is conditional on the executed contract. Terms above are the headline; the contract spells out IP, confidentiality, and termination.*
"""


def generate_onboarding(
    candidate: Candidate,
    role: str = "Founding Apprentice",
    start_date: Optional[datetime] = None,
) -> str:
    if start_date is None:
        start_date = datetime.now() + timedelta(days=10)

    days = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        days.append((i + 1, d))

    return f"""# Week 1 Plan — {candidate.name} ({role})

**Start:** {start_date.strftime("%A, %B %d, %Y")}
**Goal of Week 1:** Be shipping by Friday.

## Day 1 ({days[0][1].strftime("%A %b %d")})

- **9:00–9:30** — 1:1 with program owner. Vision, expectations, what success looks like.
- **9:30–10:30** — Aria pairing. Provision your Aria instance; first conversation; set up your default workflow.
- **10:30–12:30** — Repo orientation. Walk through `SERVICES/apprentice-studio/` as the first thing you ship into.
- **Lunch** — Owner + you, informal.
- **13:30–17:00** — Read the Apprentice OS spec (in `ARTIFACTS/founding-apprentice-job-post.md`). Form your own opinion. Write 2-3 disagreements or upgrades.

End of day: post your 2-3 upgrades to the studio Slack/Telegram. Owner reviews overnight.

## Day 2 ({days[1][1].strftime("%A %b %d")})

- **Morning** — Discuss your upgrades with owner. Lock the plan for Apprentice OS v0.1.
- **Afternoon** — Begin building. Aria as co-builder. Ship the smallest useful slice first.

## Day 3 ({days[2][1].strftime("%A %b %d")})

- **All day** — Build. Ship one slice end-to-end. (We don't wait until Day 60.)

## Day 4 ({days[3][1].strftime("%A %b %d")})

- **Morning** — First demo to owner. 15 minutes. Show, don't tell.
- **Afternoon** — Iterate based on feedback. Ship the next slice.

## Day 5 ({days[4][1].strftime("%A %b %d")})

- **Morning** — Aria Coach 1:1. How's the energy? What's friction? What's flowing?
- **Afternoon** — Ship Friday. Even small. Whatever's working today goes into the repo before EOD.
- **17:00** — Week-1 retrospective with owner. 30 minutes. What worked, what didn't, what's next.

## Days 6-7

- Rest. Seriously. The next 8 weeks are demanding.

## Access checklist (owner: complete before Day 1)

- [ ] GitHub repo access (`FPAI_Cockpit` — full read; write to `SERVICES/apprentice-studio/`)
- [ ] FPAI infra credentials (via credentials-manager, scoped to apprentice-studio + dev tools)
- [ ] Aria instance provisioned (subdomain or instance ID assigned)
- [ ] API credits topped up: Anthropic + OpenAI + Google
- [ ] Slack/Telegram channels invite sent
- [ ] Workspace ready (desk, screen, kit) if onsite
- [ ] Housing confirmed if onsite
- [ ] First 1:1 calendar invite sent

## Norms (apprentice — read these before Day 1)

- **Ship over perfect.** Whatever's working today goes in the repo today.
- **Loud confusion.** When stuck, post in the studio channel within 30 min, not 3 hours.
- **AI in the open.** Share your prompts, your stuck moments, your wins. The whole studio compounds when you do.
- **Boundaries.** No work past 19:00. No work weekends in week 1. If we ask you to break this, push back.
- **Honest feedback.** When something's broken about the program, say it the day you notice. We fix the program in real-time.
"""


def generate_welcome_message(
    candidate: Candidate,
    program_owner_name: str = "[Program Owner]",
) -> str:
    first = candidate.name.split()[0] if candidate.name else "there"
    return f"""# Welcome message draft

**To:** {candidate.email}
**Subject:** Welcome to the studio — a few things before Day 1

---

{first},

Glad you said yes.

Three things before Day 1:

1. **The Aria handoff.** Aria's already been told you're coming. When you log in, she'll know your name. You can talk to her about anything — not just code.

2. **The first 30 days are the most important.** Not because of what you ship — because of how we set the rhythm. We're going to figure out what working with each other looks like. I want you to be honest about what's not working as much as what is.

3. **You can change the program.** Everything in the studio is editable. If you read the manifesto and disagree, tell me. If the curriculum doesn't fit your project, change it. You're the founding apprentice. The shape of this is partly yours.

See you on Day 1. I'm looking forward to building with you.

—
{program_owner_name}
"""
