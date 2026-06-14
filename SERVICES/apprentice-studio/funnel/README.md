# Apprentice Studio Funnel

End-to-end recruiting pipeline. Single command interface. Every stage transition produces a draft for human review — nothing is sent without approval.

## The Funnel

```
SOURCED ─▶ CONTACTED ─▶ APPLIED ─▶ SCREENED ─▶ CHALLENGE_SENT ─▶ CHALLENGE_GRADED ─▶ INTERVIEWED ─▶ OFFER_SENT ─▶ HIRED
                                                                                                              │
                                                                                                              └──▶ DECLINED / WITHDRAWN
```

## Single command interface

From `SERVICES/apprentice-studio/`:

```bash
python funnel.py status               # Funnel snapshot + your top action
python funnel.py next                 # Just the top action
python funnel.py ingest <path>        # Ingest applications JSON
python funnel.py source <name> <email> <why>           # Add outbound prospect
python funnel.py outreach <id> "<reason>"              # Draft outbound message
python funnel.py screen [<id>]                         # Auto-screen one or all APPLIED
python funnel.py advance <id>                          # Advance + draft next-stage comms
python funnel.py decline <id>                          # Decline + draft message
python funnel.py challenge <id>                        # Generate 48-hour brief
python funnel.py grade <id> --deployed Y --code 0.7 --ai 0.9 --sys 0.6 --refl 0.8
python funnel.py dossier <id>                          # Interview prep dossier
python funnel.py interviewed <id> --score 0.85         # Log score, advance
python funnel.py offer <id>                            # Generate offer + onboarding pack
python funnel.py show <id>                             # Full candidate dump
```

## Files

```
funnel/
├── pipeline.py        # The Funnel class — state, transitions, persistence
├── stages.py          # Stage enum, Decision enum, Candidate dataclass, transitions table
├── screener.py        # Auto-screening rubric (5-criterion weighted score)
├── challenge.py       # 48-hour brief generator + grading rubric
├── interview.py       # Pre-interview dossier generator + decision frame
├── offer.py           # Offer letter + onboarding pack + welcome message
├── sourcer.py         # Outbound message drafts
├── comms.py           # Stage-transition drafts (advance / decline)
├── cli.py             # Argparse CLI (called from funnel.py at the service root)
├── data/
│   ├── pipeline.json  # Source of truth for all candidate state
│   └── sample-inbound.json  # Sample applications for testing
├── outbox/
│   └── <candidate_id>/
│       ├── outbound-message.md
│       ├── advance-to-stage-2.md
│       ├── BUILD_CHALLENGE.md
│       ├── advance-to-stage-3.md
│       ├── interview-dossier.md
│       ├── offer-letter.md
│       ├── onboarding-week-1.md
│       ├── welcome-message.md
│       └── decline.md
└── templates/         # (reserved — drafts are generated programmatically)
```

## Daily workflow (human)

Every morning:

```bash
python funnel.py status
```

Read the top suggested action. Do it. Repeat until empty.

Most actions are one of:
- Read 1-2 drafts in `outbox/<candidate_id>/`, edit if needed, send.
- Run `advance <id>` or `decline <id>` after reading the score + rationale.
- Take a 60-min interview, then run `interviewed <id> --score 0.X`.

## Data flow

1. **Inbound application** → `/apply` HTTP endpoint → adds to pipeline → auto-screens.
2. **Outbound prospect** → `funnel.py source` → `funnel.py outreach <id> "<reason>"` → drafts message.
3. **Stage transitions** → `funnel.py advance <id>` → drafts the next-stage comms artifact.
4. **Build challenge** → `funnel.py challenge <id>` (or auto-drafted on advance) → human sends → `funnel.py grade <id>`.
5. **Interview** → `funnel.py dossier <id>` (5-min read) → human takes call → `funnel.py interviewed <id>`.
6. **Offer** → `funnel.py offer <id>` → drafts letter + onboarding + welcome → human signs.

## Guardrails

- All comms drafts go to `outbox/`. Nothing is sent automatically.
- Pipeline state is persisted on every change (no in-memory loss).
- Screening is deterministic + auditable (rubric in `screener.py` is editable in plain Python).
- Stage transitions are validated against the `TRANSITIONS` table in `stages.py` — invalid moves raise.

## HTTP endpoints (from `main.py`)

- `POST /apply` — public application form ingest. Auto-screens. Returns id + score.
- `GET /funnel/status` — JSON funnel snapshot.
- `GET /funnel/candidate/{id}` — full candidate detail.

## Testing

```bash
cd SERVICES/apprentice-studio
python funnel.py ingest funnel/data/sample-inbound.json
python funnel.py status
python funnel.py screen
python funnel.py status
```

You'll see Maya, Devin, and Sage in the funnel with screening scores, and a recommended next action.
