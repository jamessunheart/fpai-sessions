---
name: service-registry-lookup
description: >-
  Look up which server a service runs on, its port, and whether it is
  intentionally stopped. Use whenever you need to call or deploy a service and
  aren't 100% sure of its host/port, or when writing code that needs to target
  the right internal URL.
---

# Service Registry Lookup

**Recommended model:** Composer 2 (pure lookup; no reasoning needed, fast and cheap is the right fit).

All service locations live in one place: `@docs/coordination/SERVICE_REGISTRY.md`. Never hardcode ports or IPs from memory — read the registry.

## Two servers

- **Primary — 198.54.123.234:** web, trading, revenue, data.
- **Secondary — 162.0.208.88:** AI, consciousness, intelligence.

## Common services (always verify against registry before use)

| Service | Server | Port |
|---|---|---|
| AI Brain | Secondary | 8101 |
| Ollama | Secondary | 11434 |
| Data Service | Primary | 8125 |
| WhaleTrack Live | Primary | 8601 |
| Nerve Center | Primary | 8120 |
| Consciousness | Secondary | 8130-8170 |
| FP Credits Gateway | Primary | 8765 |

## When writing API-routing code

```python
AI_BRAIN_URL = "http://162.0.208.88:8101"            # NOT localhost
DATA_SERVICE_URL = "http://198.54.123.234:8125"
TRADING_URL = "http://198.54.123.234:8601"
```

Prefer environment variables (`AI_BRAIN_URL`, etc.) over inlining — then there's one place to update if a service moves.

## "Stopped on purpose" list — do not restart on primary

- fpai-ai-brain, fpai-ai-chat, fpai-aria, fpai-voice-companion
- fpai-consciousness-*, fpai-analytics, fpai-flywheel

These live on the secondary now. If systemd on primary keeps trying to start them, confirm with the user before touching the unit files.

## Decision flow

1. Read `@docs/coordination/SERVICE_REGISTRY.md`.
2. Verify the service isn't on the stopped list.
3. Use the registry's host/port in your code or commands.
4. If the registry is ambiguous or stale, update it — don't paper over it.

Related: `@docs/coordination/INFRASTRUCTURE_ALLOCATION.md`.
