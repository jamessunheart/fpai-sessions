-- ========================================================================
-- Concierge v1 — initial schema
-- Multi-tenant, Postgres-native, RLS-enforced
-- ========================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ------------------------------------------------------------------------
-- Tenant context helper: every connection sets app.tenant_id
-- ------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION is_superuser_context() RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT COALESCE(current_setting('app.is_superuser', true), 'false')::boolean
$$;

-- ------------------------------------------------------------------------
-- Tenants & plans
-- ------------------------------------------------------------------------

CREATE TABLE tenants (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          text UNIQUE NOT NULL,
    name          text NOT NULL,
    plan          text NOT NULL DEFAULT 'starter',       -- starter | pro | scale | custom
    status        text NOT NULL DEFAULT 'active',         -- active | paused | churned
    industry      text,
    timezone      text NOT NULL DEFAULT 'America/Denver',
    business_hours jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata      jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tenant_features (
    tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    feature_key text NOT NULL,
    enabled     boolean NOT NULL DEFAULT false,
    config      jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, feature_key)
);

-- Client-side users (tenant admins, viewers)
CREATE TABLE client_users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email         text NOT NULL,
    name          text,
    role          text NOT NULL DEFAULT 'admin',          -- admin | viewer | billing
    password_hash text,
    last_login_at timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);

-- ------------------------------------------------------------------------
-- Agents (human operators, network-wide identity)
-- ------------------------------------------------------------------------

CREATE TABLE agents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email           text UNIQUE NOT NULL,
    name            text NOT NULL,
    phone           text,
    password_hash   text,
    status          text NOT NULL DEFAULT 'onboarding',   -- onboarding | active | suspended | offboarded
    employment_type text NOT NULL DEFAULT 'bpo',          -- bpo | contractor | client_staff
    home_org        text,                                  -- e.g. 'onebpo'
    timezone        text,
    rating_overall  numeric(3,2) DEFAULT 0.00,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE skills (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    key         text UNIQUE NOT NULL,
    name        text NOT NULL,
    category    text,                                      -- vertical | channel | language | compliance
    description text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE agent_skills (
    agent_id     uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    skill_id     uuid NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    level        text NOT NULL DEFAULT 'trainee',          -- trainee | certified | expert
    rating       numeric(3,2) DEFAULT 0.00,
    calls_scored int NOT NULL DEFAULT 0,
    certified_at timestamptz,
    updated_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (agent_id, skill_id)
);

CREATE TABLE certifications (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id      uuid NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    name          text NOT NULL,
    rubric        jsonb NOT NULL DEFAULT '{}'::jsonb,
    passing_score numeric(3,2) NOT NULL DEFAULT 0.80,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE agent_certifications (
    agent_id         uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    certification_id uuid NOT NULL REFERENCES certifications(id) ON DELETE CASCADE,
    score            numeric(3,2),
    passed_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (agent_id, certification_id)
);

CREATE TABLE agent_tenant_access (
    agent_id   uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    tenant_id  uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role       text NOT NULL DEFAULT 'agent',             -- agent | supervisor | trainer
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (agent_id, tenant_id)
);

CREATE TABLE availabilities (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id   uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    starts_at  timestamptz NOT NULL,
    ends_at    timestamptz NOT NULL,
    status     text NOT NULL DEFAULT 'scheduled',         -- scheduled | live | ended | missed
    source     text NOT NULL DEFAULT 'manual',            -- manual | recurring | auto
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX availabilities_agent_time_idx ON availabilities (agent_id, starts_at, ends_at);

CREATE TABLE ratings (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    skill_id        uuid REFERENCES skills(id),
    conversation_id uuid,
    source          text NOT NULL,                        -- ai_qa | supervisor | client | csat
    score           numeric(3,2) NOT NULL,
    rubric          jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ratings_agent_skill_idx ON ratings (agent_id, skill_id, created_at DESC);

CREATE TABLE earnings_ledger (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        uuid NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    tenant_id       uuid REFERENCES tenants(id) ON DELETE SET NULL,
    conversation_id uuid,
    kind            text NOT NULL,                        -- per_call | per_outcome | hourly | bonus | adjustment
    amount_uc       numeric(12,4) NOT NULL,
    notes           text,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX earnings_agent_time_idx ON earnings_ledger (agent_id, created_at DESC);

-- ------------------------------------------------------------------------
-- Contacts (tenant's end-customers)
-- ------------------------------------------------------------------------

CREATE TABLE contacts (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_e164 text,
    email      text,
    name       text,
    metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
    consent    jsonb NOT NULL DEFAULT '{}'::jsonb,        -- {tcpa: true, recording: true, opt_out_at: ...}
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, phone_e164),
    UNIQUE (tenant_id, email)
);
CREATE INDEX contacts_tenant_phone_idx ON contacts (tenant_id, phone_e164);

-- ------------------------------------------------------------------------
-- Conversations — the core object
-- ------------------------------------------------------------------------

CREATE TABLE conversations (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    channel            text NOT NULL,                      -- voice | sms | chat | email
    direction          text NOT NULL,                      -- inbound | outbound
    status             text NOT NULL DEFAULT 'open',       -- open | on_hold | transferred | closed
    contact_id         uuid REFERENCES contacts(id) ON DELETE SET NULL,
    agent_id           uuid REFERENCES agents(id) ON DELETE SET NULL,
    intent             text,
    skills_required    text[] NOT NULL DEFAULT '{}',
    confidence_score   numeric(4,3),
    escalation_reason  text,
    resolution_code    text,
    outcome            text,                               -- booked | quoted | voicemail | no_answer | handoff | resolved | unresolved
    external_ids       jsonb NOT NULL DEFAULT '{}'::jsonb, -- twilio_call_sid, hubspot_deal_id, etc.
    created_at         timestamptz NOT NULL DEFAULT now(),
    closed_at          timestamptz
);
CREATE INDEX conversations_tenant_time_idx ON conversations (tenant_id, created_at DESC);
CREATE INDEX conversations_agent_idx ON conversations (agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX conversations_status_idx ON conversations (tenant_id, status);

CREATE TABLE conversation_events (
    id              bigserial PRIMARY KEY,
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    event_type      text NOT NULL,                        -- utterance | tool_call | transfer | escalation | ...
    actor_type      text NOT NULL,                        -- caller | ai | agent | system
    actor_id        uuid,
    payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX conv_events_conv_idx ON conversation_events (conversation_id, id);
CREATE INDEX conv_events_tenant_time_idx ON conversation_events (tenant_id, created_at DESC);

-- Full transcript denormalized for search
CREATE TABLE transcripts (
    conversation_id uuid PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    text            text NOT NULL DEFAULT '',
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX transcripts_text_trgm_idx ON transcripts USING gin (text gin_trgm_ops);

-- ------------------------------------------------------------------------
-- Tickets + Bookings
-- ------------------------------------------------------------------------

CREATE TABLE tickets (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
    contact_id      uuid REFERENCES contacts(id) ON DELETE SET NULL,
    subject         text NOT NULL,
    body            text,
    status          text NOT NULL DEFAULT 'open',         -- open | in_progress | resolved | closed
    priority        text NOT NULL DEFAULT 'normal',
    assigned_agent  uuid REFERENCES agents(id) ON DELETE SET NULL,
    external_ids    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    resolved_at     timestamptz
);
CREATE INDEX tickets_tenant_status_idx ON tickets (tenant_id, status);

CREATE TABLE bookings (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
    contact_id      uuid REFERENCES contacts(id) ON DELETE SET NULL,
    service_type    text,
    address         jsonb,
    scheduled_start timestamptz NOT NULL,
    scheduled_end   timestamptz,
    status          text NOT NULL DEFAULT 'scheduled',    -- scheduled | confirmed | completed | cancelled | no_show
    notes           text,
    external_ids    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX bookings_tenant_time_idx ON bookings (tenant_id, scheduled_start);

-- ------------------------------------------------------------------------
-- Escalations / handoff queue
-- ------------------------------------------------------------------------

CREATE TABLE escalations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    reason          text NOT NULL,
    skills_required text[] NOT NULL DEFAULT '{}',
    priority        text NOT NULL DEFAULT 'normal',       -- low | normal | high | urgent
    status          text NOT NULL DEFAULT 'queued',       -- queued | offered | accepted | completed | abandoned
    offered_to      uuid REFERENCES agents(id) ON DELETE SET NULL,
    accepted_by     uuid REFERENCES agents(id) ON DELETE SET NULL,
    sla_deadline_at timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    accepted_at     timestamptz,
    completed_at    timestamptz
);
CREATE INDEX escalations_tenant_status_idx ON escalations (tenant_id, status, priority);

-- ------------------------------------------------------------------------
-- Knowledge base (per tenant, RLS-enforced)
-- ------------------------------------------------------------------------

CREATE TABLE knowledge_sources (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    kind       text NOT NULL,                             -- url | doc | faq | manual
    uri        text,
    title      text,
    status     text NOT NULL DEFAULT 'pending',           -- pending | crawling | indexed | failed
    last_crawled_at timestamptz,
    metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE knowledge_chunks (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id  uuid NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    chunk_idx  int NOT NULL,
    text       text NOT NULL,
    embedding  vector(1536),
    tokens     int,
    metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX knowledge_chunks_tenant_idx ON knowledge_chunks (tenant_id);
CREATE INDEX knowledge_chunks_embed_idx ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Prompt packs (per-tenant AI persona + rules)
CREATE TABLE prompt_packs (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name       text NOT NULL,
    kind       text NOT NULL DEFAULT 'voice',             -- voice | sms | chat | email
    system_prompt text NOT NULL,
    tools      jsonb NOT NULL DEFAULT '[]'::jsonb,
    examples   jsonb NOT NULL DEFAULT '[]'::jsonb,
    active     boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX prompt_packs_tenant_active_idx ON prompt_packs (tenant_id, kind, active);

-- Few-shot examples generated from human corrections (auto-training)
CREATE TABLE few_shot_examples (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    prompt_pack_id uuid REFERENCES prompt_packs(id) ON DELETE SET NULL,
    intent         text,
    input_text     text NOT NULL,
    ai_draft       text NOT NULL,
    human_revision text NOT NULL,
    skill_id       uuid REFERENCES skills(id),
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX fse_tenant_intent_idx ON few_shot_examples (tenant_id, intent);

-- ------------------------------------------------------------------------
-- Outbound campaigns
-- ------------------------------------------------------------------------

CREATE TABLE campaigns (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        text NOT NULL,
    goal        text NOT NULL,                            -- book_appointment | qualify | survey | win_back
    status      text NOT NULL DEFAULT 'draft',            -- draft | running | paused | completed
    cadence     jsonb NOT NULL DEFAULT '[]'::jsonb,       -- [{step:0, channel:'email', template_id, wait_hours}]
    targeting   jsonb NOT NULL DEFAULT '{}'::jsonb,
    budget_uc   numeric(12,2),
    started_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE campaign_contacts (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    contact_id  uuid REFERENCES contacts(id) ON DELETE SET NULL,
    phone_e164  text,
    email       text,
    step_idx    int NOT NULL DEFAULT 0,
    status      text NOT NULL DEFAULT 'pending',          -- pending | in_flight | converted | unsubscribed | bounced | complete
    next_run_at timestamptz,
    last_touch_at timestamptz,
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cc_campaign_next_idx ON campaign_contacts (campaign_id, next_run_at) WHERE status = 'pending';

-- ------------------------------------------------------------------------
-- Compliance (append-only audit log)
-- ------------------------------------------------------------------------

CREATE TABLE compliance_events (
    id              bigserial PRIMARY KEY,
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
    contact_id      uuid REFERENCES contacts(id) ON DELETE SET NULL,
    kind            text NOT NULL,                        -- tcpa_check | dnc_check | bot_disclosure | recording_consent | opt_out | time_of_day | consent_grant | consent_revoke
    result          text NOT NULL,                        -- pass | fail | granted | revoked
    jurisdiction    text,
    details         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX compliance_tenant_time_idx ON compliance_events (tenant_id, created_at DESC);
CREATE INDEX compliance_contact_idx ON compliance_events (contact_id) WHERE contact_id IS NOT NULL;

CREATE TABLE dnc_registry (
    tenant_id  uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_e164 text NOT NULL,
    source     text NOT NULL,                             -- national_dnc | state_dnc | tenant_internal | opt_out
    added_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, phone_e164, source)
);

-- ------------------------------------------------------------------------
-- Shared event outbox (for nerve-center + redis fanout)
-- ------------------------------------------------------------------------

CREATE TABLE event_outbox (
    id         bigserial PRIMARY KEY,
    tenant_id  uuid REFERENCES tenants(id) ON DELETE SET NULL,
    topic      text NOT NULL,
    payload    jsonb NOT NULL,
    published  boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX event_outbox_unpublished_idx ON event_outbox (id) WHERE NOT published;

-- ========================================================================
-- Row-Level Security
-- ========================================================================

ALTER TABLE tenant_features     ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_users        ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts            ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations       ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcripts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets             ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings            ENABLE ROW LEVEL SECURITY;
ALTER TABLE escalations         ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_sources   ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks    ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_packs        ENABLE ROW LEVEL SECURITY;
ALTER TABLE few_shot_examples   ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns           ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_contacts   ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_events   ENABLE ROW LEVEL SECURITY;
ALTER TABLE dnc_registry        ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'tenant_features','client_users','contacts','conversations','conversation_events',
    'transcripts','tickets','bookings','escalations','knowledge_sources','knowledge_chunks',
    'prompt_packs','few_shot_examples','campaigns','campaign_contacts','compliance_events','dnc_registry'
  ] LOOP
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %I USING (is_superuser_context() OR tenant_id = current_tenant_id()) WITH CHECK (is_superuser_context() OR tenant_id = current_tenant_id())',
      t
    );
  END LOOP;
END$$;

-- Tenants table readable only in superuser context by default (service layer gates access)
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenants_self_read ON tenants
    USING (is_superuser_context() OR id = current_tenant_id());

-- Earnings / ratings are joined against agents + conversations — keep RLS on
ALTER TABLE earnings_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY earnings_tenant ON earnings_ledger
    USING (is_superuser_context() OR tenant_id IS NULL OR tenant_id = current_tenant_id());

ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;
CREATE POLICY ratings_tenant ON ratings
    USING (is_superuser_context() OR conversation_id IS NULL OR EXISTS (
      SELECT 1 FROM conversations c
       WHERE c.id = ratings.conversation_id AND c.tenant_id = current_tenant_id()
    ));

-- ========================================================================
-- Updated-at triggers
-- ========================================================================

CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'tenants','client_users','agents','contacts','tickets','bookings','transcripts'
  ] LOOP
    EXECUTE format(
      'CREATE TRIGGER %I_touch BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION touch_updated_at()',
      t, t
    );
  END LOOP;
END$$;
