# Full Potential Concierge

AI-first, human-assisted customer experience platform. AI answers, AI books, AI escalates — humans handle the complex and teach the AI every day.

## Services (port map)

| Service | Port | Purpose |
|---|---|---|
| tenant-api | 8820 | Tenant CRUD, plan/feature-flag resolution, agent + client identity |
| handoff-broker | 8821 | Escalation queue, WebSocket live handoff, warm transfer, SLA timers |
| voice-router | 8822 | Twilio inbound/outbound, Realtime voice loop, tool calling, transfer |
| outbound-engine | 8823 | Campaigns, lead sourcing, cadence, AI voice dialer |
| compliance-gate | 8824 | TCPA/DNC/time-of-day/bot-disclosure/recording/consent/opt-out |
| skills-mesh | 8825 | Skill passports, routing, certifications, ratings, earnings, availability |
| knowledge-ingest | worker | Crawl tenant URLs → chunk → embed → pgvector |
| workers/auto-training | worker | Diff human-edited drafts → few-shot store |
| workers/ai-qa | worker | Post-call rubric scoring → agent skill ratings |
| agent-console | 3100 | Single pane of glass for human agents |
| client-dashboard | 3101 | Live metrics, transcripts, settings, billing |

## Multi-tenant by design

- `tenant_id` is a first-class FK on every table
- Postgres RLS enforces isolation at the DB layer
- Every service sets `SET LOCAL app.tenant_id = '<uuid>'` per request
- Shared event bus via Postgres `NOTIFY` (Redis upgrade path)

## Universal Credits

All Concierge SKUs billed in UC (1 UC = $1). See `docs/UC_SKUS.md`. Authority: `fp-credits-gateway`.

## Quick links

- Specification: `SPEC.md`
- DB schema: `db/migrations/`
- Event schema: `shared/events.py`
- UC SKUs: `docs/UC_SKUS.md`
- Dev bootstrap: `make dev`
