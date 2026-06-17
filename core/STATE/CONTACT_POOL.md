# Contact Pool Protocol

The contact pool is the private intake layer for people James may invite into a probe conversation. It is not public context and must not be exposed to public agents, story feeds, public packs, or broad scans.

## CSV Format

Required columns:

```csv
name,channel,contact,notes
Alex,whatsapp,15551234567,Met at retreat; ask gently
Sam,email,sam@example.com,FP Game contact
Tara,telegram,@tara,Already opted in by chat
```

Supported `channel` values are `whatsapp`, `email`, and `telegram`. Loaders also accept `wa` and `tg` aliases.

## Status Flow

`pending -> outreach_sent -> replied -> in_probe -> completed`

Inbound WhatsApp replies create or update a `brain_index.contact_pool` row with `source='inbound_wa'` and `status='replied'`, then seed `brain_index.probe_pool` for the probe agent.

## Privacy Rules

- Treat names, phone numbers, handles, notes, message IDs, and source context as private by default.
- Do not include contact pool rows in public packs or public agent prompts.
- Do not send template outreach unless `WHATSAPP_LIVE=1` and James has approved the batch.
- `WHATSAPP_LIVE=0` is receive-only/dry-run mode. It may parse inbound webhooks and build internal records but must not send outbound messages.
- Keep first-batch template sends to at most 10/hour until the Meta Business account is verified.

## Required WhatsApp Environment

- `WA_PHONE_NUMBER_ID`
- `WA_ACCESS_TOKEN`
- `WA_VERIFY_TOKEN`
- `WA_APP_SECRET` for `X-Hub-Signature-256` verification
- `WHATSAPP_LIVE=0` by default
- Optional `WA_TEMPLATE_RATE_LOG` path for the local owner-only template-send rate ledger. The ledger stores timestamps only, not phone numbers.

## WhatsApp Template

Template name: `conscious_chat_invite`

Language: `en_US`

Body:

```text
Hi {{1}} - Sunheart built me as an AI built to help people reach their full potential.
I'm the AI. Would you be open to a short conversation? Just reply here and I'll be right with you.
```
