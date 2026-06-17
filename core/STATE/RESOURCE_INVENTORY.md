# System Resource Inventory

**Last updated:** 2026-06-17 — full audit across 162/198/209  
**Purpose:** Self-awareness document. Every agent and build reads this before assuming a resource doesn't exist.

---

## Identity

| Resource | Value | Notes |
|---|---|---|
| System email | `sunheartai@fullpotential.ai` | IMAP live, polls every 2min on 162 |
| Telegram bot | `@sunheartbrain_bot` | Live, server-side on 162 |
| Phone number | `+15089780034` (Twilio) | SMS send/receive, $14.15 balance |

---

## Servers

| Server | IP | Role | SSH |
|---|---|---|---|
| 162 | 162.0.208.88 | Brain / build loop / AI services | root ✅ |
| 198 | 198.54.123.234 | Mail server / Zen Village | root ✅ |
| 209 | 209.74.93.72 | cPanel / WHM / outbounders.com et al | root ✅ |

---

## Credentials (reference only — values in `/etc/sh-brain/curator.env`)

| Service | Status | Location | Notes |
|---|---|---|---|
| Brevo (email) | ✅ live | `curator.env` → `BREVO_API_KEY` | Sends from `sunheartai@fullpotential.ai`, domain verified |
| Twilio (SMS) | ✅ live, $14.15 balance | `curator.env` → `TWILIO_*` | Account SID + auth token + number `+15089780034` |
| RunPod (GPU) | ✅ live | `curator.env` → `RUNPOD_API_KEY` | $50/month ceiling, scale-to-zero serverless |
| Cloudflare | ✅ live | `/opt/fpai/api_keys.json` | DNS management |
| Stripe | ✅ configured | `/opt/fpai/services/ai-automation/stripe_config.json` | Products + payment links already set up |
| OpenAI | ✅ key exists | `/opt/fpai/voice-phone/.env` | **Metered API — not flat-rate. Use sparingly, prefer claude -p** |
| Anthropic | ✅ key exists | `/opt/fpai/voice-phone/.env` | **Metered API — not flat-rate. Use claude -p (Max subscription) for $0 marginal** |
| Meta/Facebook | ⚠️ expired | `/opt/fpai/api_keys.json` | Token expired Feb 2026 — needs refresh |
| IMAP (system email) | ✅ live | `curator.env` → `SYSTEM_EMAIL_*` | `mail.fullpotential.com:993`, user=`sunheartai` |

---

## Python Libraries (server 162, system Python)

| Library | Version | What it enables |
|---|---|---|
| `playwright` | 1.58.0 | Headless browser automation (Chromium verified working) |
| `twilio` | 9.10.0 | SMS send/receive, voice calls |
| `openai-whisper` | 20240930 | Local voice transcription (no API cost) |
| `openai` | 1.12.0 | OpenAI API client (metered — use sparingly) |
| `anthropic` | 0.18.1 | Anthropic API client (prefer `claude -p` subprocess for $0) |
| `python-telegram-bot` | 20.7 | Telegram bot API |
| `fastapi` + `uvicorn` | 0.109 / 0.27 | HTTP API server |
| `aiohttp` | 3.13.2 | Async HTTP client |
| `requests` | 2.32.5 | HTTP client |
| `psycopg` | 3.3.3 | PostgreSQL async (brain_index) |

**Curator venv** (`/opt/sh-brain-src/.venv/`): psycopg, psycopg-binary, additional curator-specific packages.

---

## Databases

| DB | Host | Schema | Notes |
|---|---|---|---|
| brain_index (PostgreSQL) | localhost on 162 | `brain_index.*` | Live CRM: probe_pool, probe_sessions, corrections, thread, decisions, becoming |
| Redis | localhost on 198 | — | Port 6379 (internal only) |

### brain_index tables (active)
- `probe_pool` — contact list (outreach targets)
- `probe_sessions` — conversation history per contact
- `probe_reply_queue` — inbound replies awaiting response
- `corrections` — James's taste signals (open-model learning input)
- `thread` — live conversation thread across surfaces
- `decisions` — council decisions log
- `becoming` — per-person becoming model (stage tracking)

---

## Autonomous Loops (always-on, server 162)

| Loop | Timer | What it does | Kill switch |
|---|---|---|---|
| Build loop | every 10min | spec → codex build → claude -p review → TG | `touch /opt/fpai-build/.disabled` |
| IMAP poller | every 2min | poll sunheartai inbox → probe inbound handler | `systemctl stop fpai-imap-poller.timer` |
| Council debate | every 5min | 3-lens architecture debate → propose build | `~/.config/fpai/council/.disabled` |
| Morning digest | 08:00 Athens | daily summary → Telegram | `.digest_disabled` |

---

## Communication Surfaces

| Surface | Status | Identity |
|---|---|---|
| Email | ✅ live | `sunheartai@fullpotential.ai` — sends via Brevo, receives via IMAP |
| Telegram | ✅ live | `@sunheartbrain_bot` |
| SMS | ✅ ready | `+15089780034` via Twilio |
| WhatsApp | 🔨 building (d079) | WPPConnect self-hosted |
| Instagram | ⏳ needs fresh Meta token | Graph API |
| Mastodon | ⏳ can create autonomously | No phone required |
| Voice calls | ✅ library ready | Twilio voice, Whisper transcription |

---

## Missing / Gaps

| Resource | Why needed | Cost to add |
|---|---|---|
| 2captcha API key | CAPTCHA solving for browser signup flows | ~$2 deposit |
| Tavily API key | Real-time web search for contact discovery | Free tier |
| Hunter.io key | Email discovery from name/domain | Free: 25/mo |
| Fresh Meta token | Instagram/Facebook posting | James re-authenticates once |
| ElevenLabs key | Voice replies in Telegram | Free tier → $11/mo |
| Mastodon account | Federated social presence | $0 — can create today |

---

## Cost Constraints

- **$20/day hard ceiling** on all metered API usage
- **Subscription-first**: `claude -p` (Claude Max) + `codex` (ChatGPT Max) = $0 marginal
- **RunPod**: $50/month ceiling (scale-to-zero, ~$0 idle)
- **Twilio**: $14.15 current balance — replenish when below $5
- **Brevo**: transactional email, current plan covers outreach volume
