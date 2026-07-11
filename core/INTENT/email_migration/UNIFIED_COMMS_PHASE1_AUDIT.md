# Unified Communications MVP — Phase 1 Read-Only Audit

_2026-07-11 · Room `unified_comms` (active) · read-only, no account changes made._

Keystone held: **Gmail = identity continuity · Router = intent continuity.** Domain migration NOT resumed.

---

## EMAIL

| Item | Finding |
|---|---|
| System inbox | `sunheartai@fullpotential.ai` — IMAP live, polls every 2min on 162 (`tools/probe/imap_poller.py` present). Operational, not James's personal mail. |
| James personal | `james.rick.stinson@gmail.com` — this is the digest target. **No read access wired yet.** |
| Existing access | IMAP poller code exists + Gmail MCP available (`mcp__claude_ai_Gmail`, needs OAuth). |
| Sending identities | Gmail native "reply-from-received-alias" = identity continuity (free, already documented). Router picks sender for NEW mail. |
| DNS blockers | `jamesrickstinson.com` delegation broken (registrar → dead ns1/2.fullpotential.com). FROZEN. Does NOT block a read-only Gmail pilot. |

**Smallest safe email pilot:** read-only IMAP (or Gmail MCP OAuth, read scope) on ONE inbox → emit immutable Events via existing `shadow_adapter`. No sending. No DNS. No migration.

**Unavoidable James authorization #1:** grant read-only access to `james.rick.stinson@gmail.com` — either a Gmail app-password (IMAP, smallest scope) or approve the Gmail MCP OAuth consent. That's the only James-step for email ingestion.

---

## WHATSAPP

| Item | Finding |
|---|---|
| Existing integration | **NONE.** No WhatsApp code in repo or on 162. Greenfield. |
| Legal read path | Only Meta's official **WhatsApp Cloud API** (Business Platform) can observe/send legally. Personal-app scraping / unofficial bridges = ban + security risk → **excluded per your directive.** |
| Blocker | Cloud API requires a Business account + phone number registered to it. Personal WhatsApp cannot be read by any sanctioned method. |

**Unavoidable James authorization #2:** confirm your WhatsApp setup —
- ↳ Which account? personal app · Business app · Business Platform (Cloud API)
- ↳ Phone number + who owns it
- ↳ Whether you'll register a number on the Cloud API (the only sanctioned inbound+outbound path)

Until that's known, WhatsApp ingestion stays NOT-live by design (no unofficial fallback).

---

## VOICE — REUSE, don't rebuild

| Asset (on 162) | Status |
|---|---|
| `fpai-voice-caller.service` | running — voice webhook (`/opt/fpai/voice-caller/voice_webhook.py`) |
| `voice_pipeline.py` + `test_voice_pipeline.py` | present in sunheart-brain curator — transcription pipeline exists |
| Telegram bots | `fpai-public-bot`, `sh-brain-tgbot`, `zv-telegram-bot` all live |

**Plan:** wire the existing Telegram voice-note → transcription path to the Conversation OS reply-intent parser. No new interface built.

---

## Smallest safe connector plan (Phase 2 entry)

1. **Email:** read-only IMAP on `sunheartai@fullpotential.ai` FIRST (already have access) to validate the digest end-to-end with zero new auth. Add James's personal Gmail once auth #1 granted.
2. **WhatsApp:** blocked on auth #2 — hold. Digest ships email-only until then (honest partial).
3. **Voice:** reuse existing 162 pipeline; no build.
4. All ingestion: immutable Events (`shadow_adapter`), idempotent, cross-channel dedup, source link per item, Telegram-delivered digest, no outbound, no Brain promotion, kill switch.

## The ONLY two things routed to James
1. 🟡 Gmail read access to his personal inbox (app-password or OAuth approve).
2. 🟡 WhatsApp account type + number (so I pick the one legal path).

Everything else — ingestion, dedup, digest layers, voice wiring, routing preview — I build.
