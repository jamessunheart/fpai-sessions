-- ========================================================================
-- Conversational admin — proposal/confirm loop for config changes via SMS
-- ========================================================================

CREATE TABLE config_proposals (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    proposed_by   text NOT NULL,                        -- admin phone, email, or 'ai'
    channel       text NOT NULL DEFAULT 'sms',          -- sms | chat | api
    intent        text NOT NULL,                        -- set_hours | set_persona | toggle_feature | add_phone | etc.
    diff          jsonb NOT NULL,                       -- {path: "business_hours", old: {...}, new: {...}}
    summary       text NOT NULL,                        -- human-readable one-liner
    status        text NOT NULL DEFAULT 'pending',      -- pending | confirmed | rejected | expired
    expires_at    timestamptz NOT NULL DEFAULT now() + interval '10 minutes',
    confirmed_at  timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX config_proposals_tenant_pending_idx
    ON config_proposals (tenant_id, status) WHERE status = 'pending';

ALTER TABLE config_proposals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON config_proposals
    USING (is_superuser_context() OR tenant_id = current_tenant_id())
    WITH CHECK (is_superuser_context() OR tenant_id = current_tenant_id());

-- Optional: map an admin phone number to a tenant so inbound SMS resolves who is talking.
CREATE TABLE admin_phones (
    tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_e164  text NOT NULL,
    name        text,
    added_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, phone_e164)
);
CREATE INDEX admin_phones_phone_idx ON admin_phones (phone_e164);
