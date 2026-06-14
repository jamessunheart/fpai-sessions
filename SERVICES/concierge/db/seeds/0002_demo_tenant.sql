-- Demo tenant for development + proof sprint
INSERT INTO tenants (id, slug, name, plan, industry, timezone, business_hours, metadata)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'demo-hvac',
  'Demo HVAC Co.',
  'pro',
  'home_services.hvac',
  'America/Denver',
  '{"mon":["08:00","18:00"],"tue":["08:00","18:00"],"wed":["08:00","18:00"],"thu":["08:00","18:00"],"fri":["08:00","18:00"],"sat":["09:00","14:00"],"sun":[]}'::jsonb,
  '{"notes":"Seed tenant for local dev + proof sprint"}'::jsonb
)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO tenant_features (tenant_id, feature_key, enabled, config) VALUES
  ('00000000-0000-0000-0000-000000000001', 'inbound_voice',        true,  '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'inbound_sms',          true,  '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'booking',              true,  '{"calendar":"google_stub"}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'human_escalation',     true,  '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'realtime_voice',       true,  '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'outbound_campaigns',   false, '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'skills_mesh_routing',  false, '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'ai_qa',                true,  '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'auto_training',        true,  '{}'::jsonb),
  ('00000000-0000-0000-0000-000000000001', 'conversational_admin', false, '{}'::jsonb)
ON CONFLICT (tenant_id, feature_key) DO NOTHING;

INSERT INTO prompt_packs (tenant_id, name, kind, system_prompt, tools, examples, active) VALUES (
  '00000000-0000-0000-0000-000000000001',
  'Demo HVAC — Voice Concierge',
  'voice',
  $pp$
You are the AI Concierge for Demo HVAC Co., a residential HVAC service company in Denver, CO.
Your job: answer the phone warmly, qualify the job (heating/cooling, urgency, address), and book a service visit.
Always disclose you are an AI assistant on the first exchange. If the caller asks for a human, or you are not confident,
offer to warm-transfer to a team member. Never invent prices; use the `get_service_estimate` tool.
Current business hours are Mon-Fri 8am-6pm, Sat 9am-2pm, closed Sun.
$pp$,
  '[
    {"name":"book_appointment","description":"Book a service visit","parameters":{"type":"object","properties":{"service":{"type":"string"},"window":{"type":"string"},"address":{"type":"string"},"phone":{"type":"string"},"notes":{"type":"string"}},"required":["service","window","phone"]}},
    {"name":"get_service_estimate","description":"Ballpark estimate for a service","parameters":{"type":"object","properties":{"service":{"type":"string"},"details":{"type":"string"}},"required":["service"]}},
    {"name":"escalate_to_human","description":"Warm-transfer to a human agent","parameters":{"type":"object","properties":{"reason":{"type":"string"},"skills_required":{"type":"array","items":{"type":"string"}}},"required":["reason"]}}
  ]'::jsonb,
  '[]'::jsonb,
  true
)
ON CONFLICT DO NOTHING;
