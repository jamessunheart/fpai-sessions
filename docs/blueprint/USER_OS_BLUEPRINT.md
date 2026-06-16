# USER_OS_BLUEPRINT

Minimum viable install guide for a second FPOS user.

Status: v0.1, repo-local blueprint. This describes what FPOS actually is today, not the finished vision.

## 1. Minimum Install Checklist

Install only the parts needed to give a second user one coherent, bounded AI operating surface.

- One Chat channel: one approved owner chat, preferably Telegram or an equivalent single-thread channel. It must accept text and optional voice notes, preserve message order, and keep a conversation id.
- Memory profile: a named user profile with explicit memory permission. Minimum scopes are `none`, `session`, `personal`, and `private`. Default for a second user is `session` until they consent to durable personal memory.
- Intent taxonomy: every meaningful message is routed as one of `answer`, `capture`, `decision`, `build`, `proof`, `checkpoint`, or `reserved_class`.
- Routing rules: AI may answer, summarize, capture reversible preferences, draft safe artifacts, and ask one clarifying question. AI must stop for money movement, public sends, legal/tax posture, hiring/firing/reward, production deploys, secrets, irreversible deletes, core doctrine, and identity/relationship decisions.
- Decision card schema: each real decision card carries `id`, `question`, `context`, `recommended_default`, `options`, `owner`, `reserved_class`, `safe_default_if_unanswered`, `deadline_or_review_at`, `proof_expected`, and `status`.
- Proof ledger: every shipped or learned item records `intent_solved`, `downstream_intent_unlocked`, `proof`, `next_move`, `files_or_surface`, `tested`, `owner`, and `timestamp`.
- Safety gates: resource cap, kill switch, private-memory refusal at ingest, no outbound sends without approval, no production deploy, no secrets in prompts, and no autonomous spend beyond the configured cap.
- Access levels: `observer`, `user`, `builder`, `operator`, and `owner`. A second user starts as `user`; bots start below `operator` unless explicitly provisioned.
- Upgrade path: start with one chat plus memory capture, then add proof ledger, then routing reports, then self-refreshing surfaces, then controlled build/spec automation after proof and safety gates hold.

Minimum day-one files or services:

- A single chat adapter or manual chat transcript path.
- A memory store that can append user turns, bot turns, and profile facts.
- A routing prompt or function that classifies the intent taxonomy.
- A decision-card store, even if it is JSONL or Markdown at first.
- A proof ledger, even if it is append-only Markdown at first.
- A visible safety policy shown to the user before durable memory is enabled.
- A profile record matching the Agent Passport schema below.

## 2. What Works Today

A second user can get these capabilities on day 1 if the current repo/service pieces are installed and configured carefully:

- One-channel AI support: the system can be operated through an owner chat pattern, with text capture and bounded context assembly.
- Conversation memory: Telegram-style messages can be logged into `brain_index.tg_messages`, and useful batches can be compressed into notes for later retrieval.
- Retrieval-backed notes: `brain_index.note_chunks` supports indexed note chunks with source ids, tags, sensitivity, and embeddings.
- Basic sensitivity handling: ingest paths already distinguish public, personal, and private tiers; private-tier notes are refused from normal brain ingest.
- Correction capture pattern: explicit corrections can be stored in `brain_index.corrections` and injected back into future context so recurring mistakes become visible.
- Buildstream discipline: repo builds have specs, registry rows, tests, review notes, and merge gates.
- Proof shape: the repo doctrine and handoff surfaces already use intent solved, downstream unlock, proof, and next move.
- Safety doctrine: reserved-class boundaries, cost gates, and no-prod/no-send/no-money rules are documented and partially enforced in tools.
- Manual replication path: an operator can stand up a second-user prototype by copying the chat, memory, routing, decision, proof, and safety patterns without giving it full autonomy.

What the second user actually gets: a bounded AI companion that remembers agreed context, routes requests into safer categories, captures decisions and proof, and learns from explicit corrections. They do not get a finished autonomous operating system.

## 3. Gap Log

This gap log is intentionally non-empty. It is the replication readiness signal.

| Gap | Current reality | Needed before broad replication |
|---|---|---|
| Packaged installer | No one-command installer exists for a second user. | Scripted local/cloud install with config validation and rollback. |
| User isolation | Brain-index primitives exist, but full per-user tenancy and permission proofs are not complete. | Per-user storage boundaries, tests, and audit views. |
| Onboarding flow | No polished first-conversation flow exists. | A guided first chat that explains memory, gates, proof, and consent. |
| Blueprint feedback loop | Replication-relevant insights are not yet captured as a first-class note type. | Append-only `replication_insight.v1` capture wired from bot conversation events. |
| Access-level enforcement | Access levels are conceptual in this blueprint. | Runtime checks before tools, memory, sends, spend, and deploy actions. |
| Proof automation for second users | Proof format exists, but second-user proof ledgers are not fully automated. | A user-scoped proof ledger writer and reviewer surface. |
| Upgrade policy | Upgrade path is documented but not executable. | Versioned capability flags and migration checks. |
| CORA/Fi-Art policy | The policy is not stable enough to productize as default second-user guidance. | Stable reviewed policy before enabling related recommendations. |
| Support/ops | No operator runbook for second-user incidents exists. | Reset, export, pause, delete, and audit runbooks. |

## 4. Journey Refinement Hooks

The blueprint is a living install document. Every real user journey that exposes a gap or proves a repeatable pattern should append a replication insight and then update this section during review.

```json
{
  "schema": "user_os_journey_hooks.v1",
  "blueprint_version": "0.1",
  "layers": [
    {
      "id": "ONBOARDING",
      "version": "0.1",
      "teaches_in_first_conversation": [
        "FPOS is one bounded chat plus memory, routing, decisions, proof, and safety gates.",
        "The user chooses what memory can persist before durable memory is enabled.",
        "The system routes normal requests downstream and stops at reserved-class gates.",
        "Every useful proof or gap can improve the blueprint for the next user."
      ],
      "review_signal": "First conversation completed with memory permission, access level, and first decision/proof surface created."
    },
    {
      "id": "EVOLUTION",
      "version": "0.1",
      "updates_when": [
        "A user unlocks a new capability that works in live use.",
        "A user upgrades access level or memory permission.",
        "A chat surfaces a missing pattern, confusing instruction, safety concern, or repeatable setup shortcut.",
        "A proof row shows that a pattern worked for more than one user."
      ],
      "review_signal": "A `replication_insight.v1` row is reviewed and either closes a gap, adds a checklist item, or updates the onboarding script."
    },
    {
      "id": "UPGRADE_PATH",
      "version": "0.1",
      "version_bump_triggers": [
        "A new capability is proven live for a second user.",
        "A new safety gate is added or enforced in runtime code.",
        "A migration changes the Agent Passport schema or memory permissions.",
        "CORA/Fi-Art policy becomes stable enough for default product guidance.",
        "A gap-log item is closed by tested code or reviewed operating procedure."
      ],
      "review_signal": "Blueprint version increments and the proof ledger links the change to evidence."
    }
  ]
}
```

### Brain Index Append Mechanism

Bot conversations should append a reviewable note when they surface replication-relevant insight. The note type is:

`replication_insight.v1`

Minimum row shape:

```json
{
  "note_type": "replication_insight.v1",
  "source": "owner_chat",
  "source_conversation_id": "chat-or-thread-id",
  "source_message_id": "optional-message-id",
  "user_id": "agent-passport-user-id",
  "blueprint_version": "0.1",
  "insight_kind": "gap | proven_pattern | onboarding_confusion | safety_gate | upgrade_trigger",
  "blueprint_section": "minimum_install_checklist | what_works_today | gap_log | journey_refinement_hooks | agent_passport_schema_stub",
  "summary": "One sentence replication-relevant insight.",
  "evidence": "Short quoted or summarized evidence from the conversation.",
  "status": "new"
}
```

Review-only SQL for this append path lives at `docs/blueprint/brain_index_replication_insights.sql`. It is intentionally outside the service migration directory and is not applied by this blueprint branch. A future bot wiring build should insert into that append-only table when the classifier sees `replication_insight.v1`.

## 5. Agent Passport Schema Stub

The Agent Passport is the minimum user profile. It is not a full CRM record.

```json
{
  "schema": "agent_passport.v0",
  "user_id": "stable-user-id",
  "identity": {
    "display_name": "",
    "timezone": "",
    "locale": "",
    "role_context": ""
  },
  "goals": [
    {
      "goal_id": "",
      "description": "",
      "status": "active | paused | done",
      "proof_expected": ""
    }
  ],
  "preferred_channel": {
    "channel_type": "telegram | chat | email | other",
    "channel_id": "",
    "backup_channel": ""
  },
  "memory_permissions": {
    "default_scope": "none | session | personal | private",
    "durable_memory_allowed": false,
    "private_memory_allowed": false,
    "retention_preference": "",
    "export_or_delete_contact": ""
  },
  "access_level": {
    "level": "observer | user | builder | operator | owner",
    "granted_by": "",
    "granted_at": "",
    "limits": []
  },
  "proof_history": [
    {
      "proof_id": "",
      "timestamp": "",
      "intent_solved": "",
      "downstream_intent_unlocked": "",
      "proof": "",
      "next_move": ""
    }
  ]
}
```

Install rule: create the Agent Passport before enabling durable memory, proof automation, or any upgrade beyond `user`.
