# Email Architecture — Router-Ready Intelligence Layer

_2026-07-10 · Ember · status: DRAFT for James · supersedes ad-hoc mail setup_

## The keystone realization (James, 2026-07-10)

> **Gmail already solves identity continuity. The Router solves intent continuity. Different problems.**

- **Identity continuity** = "reply as the person they emailed." Gmail does this natively.
- **Intent continuity** = "route this conversation to the right room, state, and steward." Only the Router does this.

Design rule that falls out of this: **the email infrastructure stays dumb and stable; all intelligence lives in the Router layer above it.** Never bury Router-needed data inside Gmail-specific logic.

---

## 1. Recommended Architecture

```
                    ┌─────────────────────────────────────────┐
   inbound mail →   │  DOMAINS (sending identities)            │
  (all domains)     │  fullpotential.com/.ai · globalsky ·      │
                    │  outbounders · inbounders · coravida ·    │
                    │  jamesrick · jamesrickstinson · future    │
                    └───────────────┬─────────────────────────┘
                                    │ forward-all
                                    ▼
                    ┌─────────────────────────────────────────┐
   IDENTITY LAYER   │  Canonical Inbox — Gmail                  │
   (Gmail owns)     │  • one operational inbox                 │
                    │  • reply-from-received-alias (native)    │
                    │  • send-as for every domain (SMTP)       │
                    └───────────────┬─────────────────────────┘
                                    │ every message exposes a
                                    │ clean Event envelope (§Router Hooks)
                                    ▼
                    ┌─────────────────────────────────────────┐
   INTENT LAYER     │  ROUTER  (Conversation OS v0)            │
   (we build)       │  classify → Intent Room → Shared State  │
                    │  → Digest → Brain sync                   │
                    │  chooses SENDER for NEW mail by intent   │
                    └─────────────────────────────────────────┘
```

**Two layers, hard boundary.** Gmail is the identity/transport substrate — never modified by the Router. The Router reads Events and writes decisions. Swapping Gmail for another provider later must not touch the Router.

---

## 2. DNS Changes (per domain)

For **every** domain that sends or receives:

| Record | Value | Purpose |
|--------|-------|---------|
| **MX** | Google Workspace MX (or forwarder) | receive |
| **SPF** | `v=spf1 include:_spf.google.com include:<smtp-relay> ~all` | authorize senders |
| **DKIM** | Workspace-generated 2048-bit key, `google._domainkey` | sign |
| **DMARC** | `v=DMARC1; p=quarantine; rua=mailto:dmarc@fullpotential.com; pct=100` | policy + reporting |
| **rDNS/PTR** | on any self-hosted sending IP (162, relay) | deliverability |

Start DMARC at `p=none` for 1–2 weeks to collect `rua` reports, then tighten to `quarantine` → `reject`. Never jump straight to reject.

Reuse recipes: `reference_brevo_in_fp_mail_stack.md`, `reference_cpanel_addon_domain_deploy_recipe.md`, `reference_email_health_canary.md`.

---

## 3. Gmail Configuration

1. **Reply from received alias** — Settings → Accounts → "When replying, reply from the same address the message was sent to." (**solves identity continuity**)
2. **New-mail default** — default send-as = `james@fullpotential.com`. (Router overrides later.)
3. **Send-as** — add each domain address, verified via SMTP (§4).
4. **Forwarding** — every domain forwards inbound → canonical inbox. No siloed mailboxes.
5. **Labels** — auto-label by domain / project / intent / person / company via filters. Flat, not deep folders. Labels are **metadata the Router reads**, not Gmail-only UI sugar.

---

## 4. SMTP Configuration

- **Send-as per domain** through Workspace SMTP (`smtp-relay.google.com`) or a relay (Brevo/Postfix on 162) where a domain isn't on Workspace.
- Auth: OAuth for Workspace domains; SMTP creds (app password / relay key) for non-Workspace.
- **Router send path:** the Router calls the same send-as identities via Gmail API — it *chooses* the From, Gmail *executes* it. One send mechanism, two callers (human in Gmail UI, Router via API).

---

## 5. Router Hooks — the Event envelope

Every email, on arrival, exposes a provider-neutral envelope. **Do not require the Router to parse Gmail internals.**

```json
{
  "original_recipient":  "hello@coravida.com",
  "sender_identity":     "coravida.com",
  "from":                "lead@example.com",
  "thread_id":           "…",
  "message_id":          "…",
  "subject":             "…",
  "labels":              ["coravida", "inbound", "prospect"],
  "project":             null,        // Router fills
  "intent":              null,        // Router fills
  "person":              null,        // Router resolves → Brain
  "received_at":         "ISO-8601"
}
```

Source: Gmail API (`users.messages.get`) + a thin adapter that emits this shape. The adapter is the **only** Gmail-aware code. Everything downstream speaks Event, not Gmail.

---

## 5a. Event Store — the source of truth (James, 2026-07-10)

> **Everything derives from the Event stream, never directly from email.**

The Event store — not Gmail — is the SSOT. Email (and Telegram, SMS, forms later) are just **producers** of Events. Four properties, non-negotiable:

| Property | Meaning | Why it matters |
|----------|---------|----------------|
| **Provider-agnostic** | Event schema names no provider. `source: "gmail"` is a *field*, not a shape. Telegram/SMS/webhook emit the same envelope. | Swap Gmail → relay pool, add channels, zero downstream change |
| **Immutable** | Events are append-only. Never edited, never deleted. Corrections = a new Event that supersedes. | Auditability; no lost history; safe concurrent readers |
| **Versioned** | Each Event carries `schema_version`. Readers handle known versions; new fields are additive. | Schema evolves for years without breaking old Events |
| **Replayable** | Any derived state (Intent Rooms, Shared State, Digest, Brain, dashboards) can be rebuilt from scratch by replaying the stream. | Fix a classifier bug → replay → correct state. New view → replay → backfilled. No migrations |

**The discipline:** derived state is a *projection*, always disposable and rebuildable. If a projection and the Event stream disagree, the stream wins — rebuild the projection. Never write logic that reads Gmail directly for anything downstream; if it's not in an Event, it doesn't exist to the system.

**Event envelope, upgraded:**

```json
{
  "event_id":        "uuid",          // immutable identity
  "schema_version":  "1.0",           // versioned
  "source":          "gmail",         // provider-agnostic field, not shape
  "type":            "email.received",
  "occurred_at":     "ISO-8601",      // when it happened (from source)
  "ingested_at":     "ISO-8601",      // when we stored it
  "tenant_id":       null,            // platform partition (§7)
  "payload": {                        // the §5 envelope
    "original_recipient": "hello@coravida.com",
    "sender_identity":    "coravida.com",
    "from": "…", "thread_id": "…", "message_id": "…",
    "subject": "…", "labels": ["…"]
  }
}
```

**Storage:** append-only log — start simple (JSONL / SQLite append table on 162), graduate to a real event log (Postgres append table → NATS/Kafka) only when volume demands. The *contract* (append-only, versioned, replayable) matters more than the tech. Corrections and enrichments (Router fills `project`/`intent`/`person`) are **new Events referencing the original `event_id`**, never mutations.

---

## 6. Conversation OS — Email as Event

```
Email → Adapter (Event envelope) → Router
   → classify (domain · intent · relationship)
   → assign Intent Room
   → update Shared State
   → append to Digest
   → sync Brain (mcp__sunheart-brain)
```

The Router does all five **without modifying email infrastructure**. Adding a new Intent Room or classifier = Router change only. DNS/Gmail/SMTP untouched.

New-mail sender selection lives here: Router picks From by (intent, relationship, project); falls back to `fullpotential.com` when unsure. This is the piece Gmail structurally cannot do — and the first real Universal Router capability.

---

## 7. How this scales to 10,000 organizations

The question that forces platform design, not personal-inbox design.

**Don't:** one Workspace user per org (10k seats, unmanageable, cost-explosive).

**Do — the tenancy model:**

| Concern | Personal (today) | Platform (10k orgs) |
|---------|------------------|---------------------|
| **Identity** | Gmail aliases | **Multi-tenant domain registry** — each org = a tenant with N sending identities; one shared transport substrate |
| **Inbox** | one Gmail | **Per-tenant logical inbox** = a view over the shared Event store, filtered by tenant_id. Not 10k mailboxes |
| **Send-as** | Gmail send-as | **Relay pool** (Brevo/Postmark/SES) with per-domain DKIM; send authority scoped by tenant |
| **Router** | one Router | **Same Router, tenant-scoped state.** Every Event carries `tenant_id`; Intent Rooms / Shared State / Digest / Brain all partition on it |
| **Deliverability** | per-domain DKIM | **Per-tenant DKIM + subdomain sending** (`m.orgname.com`) so one org's reputation can't poison another's |
| **Isolation** | n/a | **tenant_id is the hard boundary** — data, reputation, and Router state never cross tenants |

**The invariant that makes it last:** the Event envelope (§5) already carries everything a tenant needs — add one field, `tenant_id`, and the personal architecture *is* the platform architecture. Same Router, same Brain sync, same Intent Rooms — just partitioned. Nothing gets redesigned; it gets a partition key.

That's the test of whether today's design is right: **can it become the 10k-org platform by adding a partition key and swapping Gmail for a relay pool — with the Router untouched?** This design passes.

---

## Migration sequence (cautious · James directive 2026-07-10)

**Order = lowest-risk first, `fullpotential.com` last with a tested rollback.** One domain fully validated before the next starts. Never batch.

| # | Domain | Risk | Why this slot |
|---|--------|------|---------------|
| 1 | jamesrickstinson.com | lowest | dormant, near-zero live mail — safe to prove the runbook |
| 2 | inbounders.com | low | minimal live traffic |
| 3 | jamesrick.com | low-med | some history (see `reference_global_sky_wp_backup.md`) |
| 4 | globalsky.com | med | live-ish |
| 5 | coravida.com | med | active project surface |
| 6 | outbounders.com | med-high | real inbound volume |
| 7 | fullpotential.ai | high | Workspace-tied — don't break existing logins |
| 8 | **fullpotential.com** | **highest** | primary inbox — last, only after 1–7 stable + rollback rehearsed |

**Per-domain runbook (repeat, one at a time):**
0. **Capture BOTH rollback artifacts first:**
   - **Config baseline** — export the full DNS zone (all record types, not just email).
   - **Functional baseline** — record current email flow with real test messages (send/receive on the live address, note the Gmail "Send As" list). Proves what "working" looked like *before* touching it.
1. Add to Workspace/relay → generate DKIM.
2. DNS: MX · SPF · DKIM · DMARC `p=none` — **additive only**, preserve every existing record (websites, subdomains, verification TXT).
3. Add Gmail send-as, verify.
4. Enable inbound forwarding → canonical inbox.
5. **VALIDATE GATE — full functional check (ALL must pass before next domain):**
   - **inbound:** test email arrives + labels correctly
   - **outbound:** Gmail "Send As" works
   - **alias replies:** reply auto-uses the received alias (reply-from-alias fires)
   - **SPF · DKIM · DMARC:** mail-tester.com ≥ 9/10, all three pass, DMARC `rua` reports clean
6. **48-HOUR OBSERVATION GATE** — even after all 6 checks pass immediately, **wait 48h before starting the next domain.** Immediate validation ≠ real-world stable. The soak window catches: delayed delivery, first DMARC `rua` reports (often 24h+ lag), forwarding loops/bounces, greylisting, and reputation edge cases — one domain at a time, before they can cascade across the fleet.
7. After 1–2 weeks of clean `rua`: tighten DMARC → `quarantine` → `reject`.

**Two-layer rollback (every domain):** config rollback = restore the exported zone · functional rollback = restore to the known-good behavior captured in the functional baseline. Never proceed to the next domain without both artifacts in hand.

**Rollback (rehearsed before domain 8):** restore snapshotted zone (MX back) + remove send-as. Gmail stays canonical throughout, so **no data loss on rollback** — worst case is inbound briefly routes to the old MX.

**★ Credential gate (honest):** external DNS/registrar + Workspace-admin edits are hard-blocked to me (creds/prod). I produce each domain's exact record set + run the VALIDATE GATE checks; you apply the DNS edits (or hand me registrar/cPanel access and I execute). First move waits on that.

**Once 1–8 stable:** email becomes the Router's first communication interface — the first channel feeding the immutable Event stream (§5a).

---

## Deliverables checklist

- [x] **Migration plan** — see sequence above (lowest-risk first, fullpotential.com last).
- [ ] **Testing checklist** — send + receive per domain · reply-from-alias fires · SPF/DKIM/DMARC pass (mail-tester.com ≥9/10) · no NDRs · Event envelope emits correct fields.
- [ ] **Rollback plan** — DNS changes are reversible (keep old zone file snapshot per domain); forwarding is a toggle; send-as is removable. Rollback = restore prior MX + remove send-as. No data loss because Gmail stays canonical throughout.

---

## Lessons learned (update after EACH domain, before starting the next)

**Rule (James, 2026-07-10):** after each successful domain, record what the real world taught us here — *before* proceeding. The migration process itself becomes reusable platform knowledge. Each entry sharpens the runbook for the next domain and, eventually, the 10k-org playbook.

Per domain, capture: what differed from the plan · any DNS/host quirk (cPanel field limits, propagation time, provider behavior) · deliverability surprises (mail-tester score, DMARC report oddities) · anything that should change the standard runbook.

| # | Domain | Date done | Key lessons → runbook changes |
|---|--------|-----------|-------------------------------|
| 1 | jamesrickstinson.com | _pending_ | _(fill after 48h soak)_ |
| 2 | inbounders.com | — | — |
| … | … | … | … |

When a lesson generalizes, promote it into the runbook steps above (not just this log) so the next domain inherits it automatically.

---

## The playbook IS Version 1 of the Router (James, 2026-07-10)

> **Every manual step in this migration is future product functionality. The playbook is the Router's product roadmap.**

Don't just document the process — read each manual step as a capability the Router will eventually own. Platform knowledge compounds when the doing becomes the building. Each row below is a Router feature, seeded by the manual step we run first.

| Manual step (playbook v1) | → Automated capability (Router) | Product form |
|---------------------------|----------------------------------|--------------|
| Read/inventory the zone by hand | DNS discovery + diff engine | API: `GET /domain/{d}/zone` |
| Add MX/SPF/DKIM/DMARC records manually | DNS provisioning (registrar/cPanel API) | **Domain onboarding wizard** |
| Confirm records via `dig` | Automated DNS verification poller | Verification service |
| 6-point validate gate (manual sends) | Automated inbound/outbound/alias test harness | **Validation gate as a service** |
| mail-tester score check | Continuous deliverability scoring | Health check job |
| Watch DMARC `rua` reports | Continuous SPF/DKIM/DMARC monitoring + parsing | **Deliverability dashboard (live)** |
| 48h manual soak | Automated soak window + anomaly alerting | Observation gate w/ alerts |
| Restore zone / remove records to roll back | Snapshot + **one-click rollback** | Rollback button |
| Repeat per domain, log lessons | Fleet-wide domain health board | **Health dashboard (live)** |
| Tighten DMARC none→quarantine→reject | Policy-progression automation | Reputation autopilot |

**The compounding rule:** for 10k orgs, none of this can be manual. So each domain we migrate by hand is a spec-in-disguise — the manual run *is* the requirements-gathering for its automated replacement. When a step stabilizes across 2–3 domains, it graduates to a build spec (`SPEC_*`) and becomes a Router capability. The migration doesn't just move email; it **writes the platform's backlog by being run.**

Related doctrine: the Sunheart Rule (route every action to the lowest tier — here, human step → AI capability) · Three Rs (this is Recursion: the system improving how it does the work) · `feedback_standing_capability_proof_back.md` (each automated step must prove back, not silently exist).

### The evolution loop (James, 2026-07-10 · generalizes past email)

> **Every manual process becomes a product specification. Every repeated manual process becomes an automation. Every successful automation becomes a platform capability.**

```
Manual → Playbook → Specification → Automation → Platform → Intelligence
   ▲                                                              │
   └──────────────── each capability enables new manual frontiers ┘
```

- **Manual** — do it by hand once (this migration).
- **Playbook** — write down the repeatable steps (this doc).
- **Specification** — a step that repeats becomes a `SPEC_*`.
- **Automation** — the spec is built; the step runs itself.
- **Platform** — the automation generalizes across domains/tenants/orgs.
- **Intelligence** — the platform's accumulated runs teach the system to do it better than any manual operator could.

This is the growth engine for the whole **Conversation OS**, not just email: every operation performed today is tomorrow's product feature. The discipline is to never let a manual process stay merely *done* — always ask which rung it's on and push it up one. Email migration is simply the first process to walk the full ladder end-to-end.

**★ Promoted to canonical doctrine:** this loop + event-sourcing generalized into a system-wide design principle — `docs/codex/EVENT_SOURCED_PROCESS_PRINCIPLE.md` — applying equally to WhatsApp, Telegram, meetings, recruiting, treasury, CRM, support, Camp Zen, and growth. Email is its reference implementation.

---

## Open items for James

None blocking. Reversible build. On approval I execute domain-by-domain, fullpotential.com last, DMARC starting at `p=none`. Docs committed 2026-07-10.
