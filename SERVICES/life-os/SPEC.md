# Life OS — Personal Operating System

**Service:** `life-os`
**Port:** 8190
**Stack:** FastAPI + Tailwind CSS + Vanilla JS
**Storage:** JSON files (zero-dependency, portable)

---

## Prime Directive

> Protect your attention. Convert it into finished outcomes.
> Route outcomes into sustainable wealth and love.

Life OS is a daily command center that turns dispersion into directed power.
It replaces willpower with structure, mood with ritual, and chaos with lanes.

---

## Architecture

```
SERVICES/life-os/
├── app/
│   ├── main.py          # FastAPI server (all routes)
│   ├── models.py         # Pydantic models
│   ├── storage.py        # JSON file persistence
│   └── static/
│       └── index.html    # Single-page dashboard
├── data/                  # Runtime JSON storage
│   ├── days/             # Daily logs (YYYY-MM-DD.json)
│   ├── tickets.json      # O System ticket board
│   ├── finances.json     # Financial cockpit snapshot
│   └── config.json       # User preferences & goals
├── requirements.txt
├── Dockerfile
└── SPEC.md
```

---

## 10 Modules

### 1. Daily Command Center
**Morning Ritual (12 min on waking):**
- **Condition:** Rate sleep (1-10), body (1-10), mind (1-10)
- **Position:** Choose mode — Build / Earn / Connect / Restore
- **Decision:** Pick 1 outcome + smallest next step

**Deep Work Block:**
- 25-50 min timer (configurable)
- Before any messaging

**Sunset Close:**
- Capture wins (freeform text)
- Decide tomorrow's 1 outcome
- Shut the loop (mark day complete)

**Data:** `data/days/YYYY-MM-DD.json`

### 2. Four Lanes
| Lane | Scope |
|------|-------|
| A: Treasury | Cashflow, yield, risk-managed moonshots |
| B: Build | Full Potential AI / O System |
| C: Promotion | Reach, trust, conversion |
| D: Love/Body/Spirit | Relationships, wellness, nature, music |

**Rule:** Each day = 1 primary lane + 1 supporting lane. Not four mains.

### 3. Steward Team
Four virtual roles (can map to real people or AI agents):

| Role | Responsibility |
|------|---------------|
| Chief of Staff | Calendar, deep work protection, voice-note tickets, follow-up |
| Ops Builder | Automation, system integration, tool stability |
| Treasury Operator | Weekly reporting, risk flags, yields, position sizing, runway |
| Media Operator | Daily publishing, landing pages, reels, message consistency |

Each role shows: assigned person/agent, current focus, open tasks, last activity.

### 4. Financial Cockpit
One-page weekly dashboard:
- **Runway** (months of burn remaining)
- **Yield earned** (week / month)
- **Liquid reserves** ($)
- **Exposure by tier:** Stable / Growth / Moonshot (%)
- **Red flags** (list of concerns)
- **Hard rule indicator:** Moonshot cap vs liquid net worth

### 5. Revenue Engine
Single "cash-now" offer tracker:
- **Offer name** and clear deliverable
- **Price point**
- **Pipeline:** leads → calls → sales
- **Goal:** 3 sales before expanding scope
- **Funnel status:** landing page, intake form, sales script (checkboxes)

### 6. O System (Ticket Board)
Every idea becomes a ticket:
- **Title**
- **Definition of done**
- **Proof artifact** (what proves it's done)
- **Verifier** (who checks)
- **Time estimate**
- **Status:** backlog → in-progress → verify → done

Daily goal: ship 1 small module or improvement.

### 7. Content Metronome
Daily content triad tracker:
- [ ] **Clarity Transmission** (60-90 sec video/audio)
- [ ] **Proof Post** (what shipped / what worked)
- [ ] **Invitation** (offer or event)

Weekly streak counter. Consistency = amplifier.

### 8. Relationship Capital
- **Golden Hours:** 2 per week, no phone, pure presence (log them)
- **Repair Loop:** Tensions handled within 48 hours
- Relationship health pulse (simple green/yellow/red per key person)

### 9. Environment Zones
Two zones with checklist adherence:
- **Creation Sanctuary:** One desk, one device, no clutter, ritual playlist
- **Rest Temple:** No screens, low light, breathwork, sleep priority

### 10. 30-Day Overseer Plan
| Week | Focus |
|------|-------|
| 1 | Stabilize attention + dashboard + daily ritual |
| 2 | Lock one offer + funnel + publish daily |
| 3 | Delegate aggressively + ticketize everything |
| 4 | Review metrics, prune commitments, double down |

---

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve dashboard |
| GET | `/api/today` | Get today's day record |
| POST | `/api/morning` | Submit morning ritual |
| POST | `/api/sunset` | Submit sunset close |
| GET | `/api/days/{date}` | Get specific day |
| GET | `/api/days` | List recent days (last 30) |
| GET | `/api/tickets` | Get all tickets |
| POST | `/api/tickets` | Create ticket |
| PATCH | `/api/tickets/{id}` | Update ticket |
| GET | `/api/finances` | Get financial snapshot |
| POST | `/api/finances` | Update financial snapshot |
| GET | `/api/config` | Get user config |
| POST | `/api/config` | Update user config |
| GET | `/api/streaks` | Get content & ritual streaks |
| GET | `/health` | Health check |

---

## Design Principles

1. **Calm UI** — Dark theme, muted colors, generous whitespace
2. **One screen** — Everything visible without drilling down
3. **Ritual-first** — Morning flow is the hero, not a sidebar
4. **No friction** — Click to log, not forms to fill
5. **Portable** — JSON files, no database, runs anywhere
