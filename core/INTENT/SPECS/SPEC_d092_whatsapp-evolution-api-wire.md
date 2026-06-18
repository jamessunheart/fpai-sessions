# SPEC d092 — WhatsApp Wire (Evolution API already deployed)

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What
Wire the Evolution API WhatsApp instance (already running on 198:8081) into the One Chat thread. Evolution API is live, authenticated, webhook-configured. Missing: (1) a WhatsApp number connected via QR scan, (2) a webhook receiver on port 8774.

## Why
WhatsApp reaches people where they already are. The infrastructure is 100% deployed. One QR scan from James + webhook receiver = WhatsApp as a full One Chat surface alongside Telegram and email.

## Deliverables

### `tools/hermes/whatsapp_adapter.py`
- `send_message(phone, text)` → Evolution API POST /message/sendText
- `send_media(phone, url, caption)` → media messages
- `parse_webhook(payload)` → normalize inbound WA message to One Chat format
- Writes inbound messages to `brain_index.thread` with `surface='whatsapp'`

### `tools/hermes/whatsapp_webhook.py`
- FastAPI endpoint at port 8774 `/wa/webhook` (Evolution API already configured to POST here)
- Receives all WA events, routes to probe inbound handler or One Chat
- Responds within 500ms (WA requirement)

### systemd service: `fpai-whatsapp-webhook.service`
- Runs uvicorn on port 8774 on server 198
- EnvironmentFile=/etc/sh-brain/curator.env

### QR generation helper
- Script: `tools/hermes/whatsapp_connect.py --generate-qr`
- Calls Evolution API to create instance + fetch QR code
- Outputs QR as terminal ASCII or saves PNG for James to scan

## Gates
- `WHATSAPP_ENABLED=1` env flag (off until QR scanned)
- API key: `bda21649d071ba9384f6f691e0ba16f10828980495c1b72f` already in Evolution API
- Inbound messages → probe handler (if known contact) OR new probe_pool entry (if unknown)
- Never send unsolicited bulk messages via WhatsApp (ToS + spam risk)

## James action required (one-time)
After build merges: run `python3 tools/hermes/whatsapp_connect.py --generate-qr` → scan QR in WhatsApp on phone → done.

## Proof
- Webhook receives test event from Evolution API
- Inbound WA message appears in brain_index.thread with surface='whatsapp'
- Send + receive round-trip proven
