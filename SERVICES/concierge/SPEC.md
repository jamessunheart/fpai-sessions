# Concierge — Platform Specification v1.0

## Product

Hybrid AI+human customer experience for SMBs, first vertical Home Services. AI voice + chat concierge that answers, qualifies, books, and escalates; human agents (OneBPO + Full Potential Network) handle everything AI cannot.

## Architecture principles

1. **Multi-tenant first.** `tenant_id` on every row; Postgres RLS everywhere.
2. **Feature-flagged dark-ship.** Build behind flags, enable per-tenant.
3. **Plan-gated.** Starter / Pro / Scale SKUs gate features via `tenant_features`.
4. **AI-native ops.** AI drafts replies, QAs calls, routes skills, trains itself.
5. **Conversational admin.** Clients configure via SMS/chat → diff → confirm.
6. **Human-layer as first-class surface.** Agent console is the operating system, not an afterthought.
7. **Compliance by default.** Every outbound is gated at compliance-gate.
8. **UC-priced.** All billing flows through `fp-credits-gateway` (1 UC = $1).
9. **Event-driven.** Conversation is the core object; every state change is an event.

## Conversation object

```
Conversation {
  id, tenant_id, channel, direction, status,
  caller_identity, contact_id?, agent_id?, skills[], intent?,
  confidence_score, escalation_reason?, transcript[], events[],
  created_at, closed_at, resolution_code?
}
```

Channels: voice | sms | chat | email.  Directions: inbound | outbound.

## Core services — see `README.md` for port map

### tenant-api (8820)
Tenant + client user CRUD. Plan → feature flag resolver. Agent identity issuance. Client dashboard backs onto this.

### voice-router (8822)
Twilio webhooks → tenant resolution → OpenAI Realtime (or STT+LLM+TTS parallel pipeline) → tool calling (book, quote, escalate) → warm transfer. Streams partial transcripts to handoff-broker.

### handoff-broker (8821)
Escalation queue with skill tags. Matches conversation → agent via skills-mesh. Warm-transfers live voice (Twilio `<Dial>` with whisper). Tracks SLA timers + redelivers on miss.

### compliance-gate (8824)
Pre-outbound gate: TCPA/DNC lookup, time-of-day window, state two-party recording rules, bot-disclosure enforcement, consent + opt-out registry. Append-only `compliance_events` audit log.

### skills-mesh (8825)
Skill passport per agent. Routing by (intent, skill, certification, rating, availability). AI-QA scores feed into per-skill ratings. Earnings ledger accrues per call/outcome.

### outbound-engine (8823)
Campaign CRUD, lead list ingestion (Apollo/Hunter + CSV), multi-touch cadence (email/SMS/AI-call), hand-off to voice-router when contact answers, all gated through compliance-gate.

### knowledge-ingest (worker)
Per-tenant URL/doc crawler → chunker → embed → pgvector with RLS. Re-crawls weekly. Serves `/tenant/:id/retrieve` to voice-router.

### workers
- **auto-training**: every human-edited draft becomes a few-shot example keyed by tenant + intent
- **ai-qa**: post-call LLM rubric scorer → ratings on skills_mesh
- **conversational-admin**: inbound SMS intent parser → propose config diff → confirm

## Data model (high level)

See `db/migrations/0001_init.sql`. RLS enforced via `app.tenant_id` GUC set per connection.

## Event bus

Postgres `NOTIFY concierge_events, '<json>'` for v1. Redis Streams upgrade path defined in `shared/events.py`.

## Build strategy

Stream A (autonomous): infrastructure + services behind flags, all tests green.
Stream B (staged rollout): enable M1 → M7 per flag as human-in-loop validates each layer.

Milestones: see `.cursor/plans/fpai_onebpo_hybrid_cx_*.plan.md` §15b.
