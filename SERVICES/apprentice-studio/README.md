# Apprentice Studio

> **AI-native studio building products that expand humans, not replace them.**
>
> AI holds the program down. Humans make the calls that matter.

The Apprentice Studio is a living lab inside FPAI for training AI-native builders and shipping regenerative products. AI agents own day-to-day program operations (recruiting, curriculum, mentoring, comms, funding, ops). The human owner makes vision, hire, money, and partnership decisions.

## Core Philosophy

- **Apprentices keep majority equity** in what they build (70/20/10 split: apprentice / studio / cohort pool).
- **AI is staff, not subject matter.** Aria is a permanent collaborator for every apprentice.
- **Ship by week 8 or pivot.** The studio's currency is shipped products, not curriculum hours.
- **Three lenses for every project**: regenerative, sovereignty-respecting, consciousness-expanding. Hit 2 of 3 or it doesn't ship under the studio.

## The Eight AI Agents

| Agent | Role | File |
|---|---|---|
| Studio Director | Orchestrator, weekly review, escalations | `agents/studio_director.py` |
| Recruiter | Drafts/posts roles, screens applicants, schedules interviews | `agents/recruiter.py` |
| Curriculum | Builds & updates curriculum, weekly assignments, progress tracking | `agents/curriculum.py` |
| Builder Mentor | Pairs with each apprentice as AI co-builder | `agents/builder_mentor.py` |
| Comms | Manifesto, public posts, demo day plan, alumni newsletter | `agents/comms.py` |
| Funding | Tracks leads, drafts pitches, researches grants/sponsors | `agents/funding.py` |
| Operations | Budget tracking, retreat logistics, contracts, IP/legal | `agents/operations.py` |
| Aria Coach | 1:1s with each apprentice on values, energy, alignment | `agents/aria_coach.py` |

## Directory Layout

```
SERVICES/apprentice-studio/
├── README.md                    # this file
├── main.py                      # FastAPI entry + agent boot
├── orchestrator.py              # Studio orchestrator (extends aria-command pattern)
├── requirements.txt
├── agents/                      # 8 agents (base + 8 specialised)
│   ├── base.py
│   ├── studio_director.py
│   ├── recruiter.py
│   ├── curriculum.py
│   ├── builder_mentor.py
│   ├── comms.py
│   ├── funding.py
│   ├── operations.py
│   └── aria_coach.py
├── STATE/                       # source of truth for the program
│   ├── PROGRAM.md               # current phase, milestones, next decisions
│   ├── COHORT_1.json            # applicants, apprentices, projects, status
│   ├── BUDGET.json              # spend tracking
│   └── DECISIONS.md             # decision log (every yes/no with rationale)
├── ARTIFACTS/                   # AI-generated drafts ready for human review
│   ├── founding-apprentice-job-post.md
│   ├── manifesto.md
│   ├── cohort-1-application.md
│   ├── 90-day-plan.md
│   ├── funding-leads.md
│   └── studio-site-outline.md
├── triggers/                    # proactive cadence
│   ├── cron.yaml
│   └── heartbeat.py
└── scripts/
    └── (deploy + ops helpers)
```

## Proactive Cadence

| When | What | Where |
|---|---|---|
| Daily 7am | Status pulse: shifts, blocks, decisions needed | Telegram via `aria-bridge` |
| Weekly Monday | Full review with metrics + recommendations + drafts | NOW.md + Telegram |
| On milestone | Auto-drafts next artifact | `ARTIFACTS/` + inbox |
| On block >24h | Escalates with recommended default | Telegram |
| Per apprentice daily | Aria Coach check-in | Aggregated into weekly digest |

## Human-Only Decisions

AI runs the operations. The human owner owns:

- Final yes/no on hires, apprentice acceptance, partnerships, spend > $5k.
- Vision drift calls (program drifting from "tools that expand humans").
- Public face moments (interviews, keynotes, big partnerships).
- Apprentice 1:1s at acceptance, mid-program, demo day.

## Risk Guardrails

- AI cannot send external messages (applicants, funders, partners) without explicit human approval. **Drafts only.**
- AI cannot spend money. Only flags spend needed.
- All decisions logged in `STATE/DECISIONS.md`.
- Weekly review surfaces anything autonomous that the human should know about.

## Success Bar (12-month)

Hit 4 of 6 to continue past cohort 1:

1. Founding apprentice still active or transitioned to lead.
2. Cohort 1 completed.
3. 3-5 shipped products live in production.
4. $50k+ revenue from at least 1 of those products.
5. 3 case studies + 1 short film of the process.
6. 20+ qualified cohort 2 applicants from cohort 1's signal alone.

## Status

**Phase**: Founding apprentice search.
**Next milestone**: Founding apprentice hired (target: 30 days from program start).
**See**: `STATE/PROGRAM.md` for live status.

## Run Locally

```bash
cd SERVICES/apprentice-studio
pip install -r requirements.txt
python main.py
```

Spawns the orchestrator, registers all agents, runs scheduled triggers.
