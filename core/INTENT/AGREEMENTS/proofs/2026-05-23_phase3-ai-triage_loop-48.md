---
loop: 48
slug: phase3-ai-triage
title: Sunheart Flow Spine · Phase 3 · AI Triage layer LIVE · stream-aware routing
date: 2026-05-23
shipped_by: Ember (substrate-side · ~30 min from spec to first triage)
---

# Proof · Loop 48 · Phase 3 AI Triage LIVE

## What shipped

Every CAPTURED item now gets auto-classified by Claude · assigned a Stream (1-4) · routed to AI/Human/Both lane · moved to DISTILLED · with rationale comment. Runs every 5 minutes via cron on the brain server.

## The vision now in motion

Per James's "3 STEPS" diagram + "3 streams · 1 fastest" priority architecture:

- Stream 1 (⚡ Rapid Current) — fastest moving · blockers · cash-impacting
- Stream 2 (🌀 Active Flow) — important · in-motion · this-week
- Stream 3 (🍃 Slow River) — later · backlog
- Stream 4 (💤 Dormant Pool) — catch-all · vague · parked

AI does Layer 2 (Routing + Visibility) of the diagram. James moves toward Captain's Lounge Mode.

## End-to-end flow now alive

```
TG voice memo → Whisper → Linear CAPTURED (Phase 2 wire)
   ↓ (≤5 min)
AI Triage reads · classifies · sets Stream label · routes
   ↓
DISTILLED · with comment: stream + domain + route + next-action + reasoning
   ↓ (future Phase 3.5)
If AI-only · auto-spawn execution in AI EXECUTING
If Human-needed · file james_ask via reverse channel (Phase 2.5 LIVE)
```

## Files shipped

| File | Role |
|---|---|
| `SERVICES/sunheart-brain/curator/triage.py` (new · 320 lines) | Pulls CAPTURED · Claude classify · updates Linear |
| `/opt/sh-brain-src/curator/triage.py` (server) | Production deploy |
| `crontab -e` (server · root) | `*/5 * * * * python -m curator.triage >> /var/log/sh-brain-triage.log 2>&1` |
| `/var/log/sh-brain-triage.log` (server) | Run log |

## Verification

- ✅ Both existing CAPTURED items triaged on first manual run:
  - **FUL-7** ("Testing this right now... does this work?") → Stream 4 (Dormant) · domain ops · AI-only · correctly identified as a test
  - **FUL-6** ("🌊 First flow · the river begins") → Stream 1 (Rapid) · domain ops · AI-only · correctly identified as real first-flow item
- ✅ Both moved CAPTURED (0) → DISTILLED (2)
- ✅ Triage comments visible in Linear with rationale
- ✅ Idempotent: re-running skips already-triaged items (TRIAGE_MARKER detection)
- ✅ Cron installed: every 5 min · output logged to /var/log/sh-brain-triage.log

## Tunables (env-overridable)

| Env var | Default | Purpose |
|---|---|---|
| `LINEAR_TEAM_ID` | FUL UUID | Team to triage |
| `CURATOR_ANTHROPIC_MODEL` | claude-sonnet-4-20250514 | Classifier model |
| `TRIAGE_MAX_PER_RUN` | 5 | Safety cap per cron tick |

## Classification prompt

The prompt names CORA Nation umbrella · 4 pillars · Stream/Route/Domain vocabulary · so Ember's classification reflects the actual architecture.

## Bugs found + fixed during build

- Linear GraphQL: `String!` rejected for ID-typed variables → switched to `ID!`
- Env loading: `/etc/sh-brain/curator.env` has parens in values → can't `source` from shell → added direct Python parser in triage.py
- Python `.format()` collided with literal `{}` in prompt's JSON schema example → switched to `__TOKEN__` placeholders + `.replace()`

## Reversibility

HIGH. Rollback:
```
ssh brain-server
crontab -l | grep -v "curator.triage" | crontab -
rm /opt/sh-brain-src/curator/triage.py
```
No Linear data is destroyed · only state-transitions + comments added · all visible in Linear UI activity log.

## What's next (Phases 4-6)

- **Phase 3.5** · Auto-execute AI-only items (move DISTILLED → AI EXECUTING · dispatch sub-agent · post result)
- **Phase 3.6** · Auto-file Human-needed items to james_ask (TG asks for ratification)
- **Phase 4** · Visibility layer · `/cockpit/river` view + flow-health % in alignment footer
- **Phase 2-ext** · WhatsApp + Email + Form input gateways

## Composition

- `[[project-sunheart-flow-spine]]` — update to mark Phase 3 LIVE
- `[[project-james-ask-reverse-channel]]` — Phase 3.6 will pipe Human-needed items through this
- `[[reference-cora-nation-architecture]]` — the architecture the classifier prompt names
- `[[feedback-no-outsourcing-to-james-what-substrate-can-do]]` — triage IS the substrate doing the routing James used to do manually
