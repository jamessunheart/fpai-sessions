# System Resource Inventory

**Last updated:** 2026-06-17 — deep audit across 162/198/209  
**Purpose:** Self-awareness document. Every agent and build reads this before assuming a resource doesn't exist. **CHECK HERE FIRST.**

---

## Identity

| Resource | Value | Notes |
|---|---|---|
| System email | `sunheartai@fullpotential.ai` | IMAP live, polls every 2min on 162 |
| Telegram bot (main) | `@sunheartbrain_bot` | Live, server-side on 162 |
| Telegram bot (Kai) | Separate token | `KAI_BOT_TOKEN` in `/etc/sh-brain/kai.env` |
| Phone number | `+15089780034` (Twilio) | SMS send/receive, $14.15 balance |
| James phone | `+19252397291` | Stored in voice-phone/.env |

---

## Servers

| Server | IP | Role | SSH |
|---|---|---|---|
| 162 | 162.0.208.88 | Brain / build loop / AI services / AppFlowy / n8n | root ✅ |
| 198 | 198.54.123.234 | Mail / Zen Village / Concierge platform / WhatsApp | root ✅ |
| 209 | 209.74.93.72 | cPanel / WHM / web hosting (39 domains) | root ✅ |

---

## Local LLM Inference — LIVE on 162 (T1 tier, $0, full sovereignty)

**Ollama running at `http://localhost:11434`** — these models available RIGHT NOW, no API cost:

| Model | Size | Best for |
|---|---|---|
| `llama3.1:8b` | 8B | General reasoning, drafts |
| `llama3.2:3b` | 3B | Fast routing, classification |
| `mistral:7b` | 7B | General, instruction following |
| `deepseek-coder:6.7b` | 6.7B | Code generation |
| `qwen2.5-coder:7b` | 7B | Code, strong on Python |
| `codellama:7b` | 7B | Code completion |
| `phi3:mini` | 3.8B | Ultra-fast, low RAM |
| `nomic-embed-text` | — | Embeddings (semantic search) |

**Intelligence ladder updated:** T1 is LIVE, not future. Route high-volume low-stakes tasks to Ollama before escalating to claude -p.

---

## Messaging / Communication — LIVE

| Surface | Status | Where | Notes |
|---|---|---|---|
| Email | ✅ live | `sunheartai@fullpotential.ai` | Sends via Brevo, receives via IMAP poller (2min) |
| Telegram | ✅ live | `@sunheartbrain_bot` on 162 | Main bot |
| **WhatsApp** | ✅ DEPLOYED | **198 — Evolution API v2.3.7** | `localhost:8081`, API key in curator.env, webhook → port 8774 |
| SMS / Voice | ✅ ready | Twilio `+15089780034` | $14.15 balance, library installed |
| Voice transcription | ✅ ready | OpenAI Whisper (local, 162) | No API cost |

**WhatsApp is already deployed (Evolution API on 198).** d079 just needs to wire the webhook receiver, not deploy new infrastructure.

---

## AI / ML Services

| Service | Key location | Status | Notes |
|---|---|---|---|
| Claude (subscription) | `/root/.config/fpai/claude.env` | ✅ $0 marginal | `claude -p` — USE THIS FIRST |
| Codex (OpenAI) | system | ✅ $0 marginal | `codex` — USE THIS FIRST |
| Ollama (local) | localhost:11434 | ✅ $0, sovereign | 9 models available (see above) |
| OpenAI API | `/opt/fpai/voice-phone/.env`, `ai-brain/api_keys.env` | ✅ key exists | **Metered — minimize use** |
| Anthropic API | same | ✅ key exists | **Metered — prefer claude -p** |
| Gemini API | `/opt/fpai/aria-command/.env` | ✅ key exists | Google — metered |
| xAI API | `/opt/fpai/ai-brain/api_keys.env` | ✅ key exists | Grok — metered |
| Together.ai | same | ⚠️ may be expired | Check before use |
| Groq | same | ⚠️ may be expired | Check before use |
| RunPod | `/etc/sh-brain/curator.env` | ✅ live | GPU serverless, $50/mo ceiling |
| Mem0 | `/opt/fpai/aria-command/.env` | ✅ key exists | Cross-session AI memory |

---

## Credentials (reference — values in stated locations, never in git)

| Service | Status | Location | Notes |
|---|---|---|---|
| Brevo (email) | ✅ live | `curator.env` → `BREVO_API_KEY` | Sends from `sunheartai@fullpotential.ai` |
| Twilio | ✅ live, $14.15 | `curator.env` → `TWILIO_*` | SID + token + `+15089780034` |
| RunPod | ✅ live | `curator.env` → `RUNPOD_API_KEY` | $50/mo ceiling |
| Cloudflare | ✅ live | `/opt/fpai/api_keys.json` | DNS management |
| Stripe | ✅ configured | `/opt/fpai/services/ai-automation/stripe_config.json` | Products + payment links + 50% pilot coupon |
| Evolution API (WhatsApp) | ✅ live | see below | Key: `bda21649...` in curator.env (add) |
| Supabase | ✅ key exists | `/opt/fpai/aria-command/.env` | Cloud Postgres + auth |
| OpenAI (metered) | ✅ key exists | `/opt/fpai/voice-phone/.env` | Metered — minimize |
| Anthropic (metered) | ✅ key exists | `/opt/fpai/voice-phone/.env` | Metered — minimize |
| Gemini | ✅ key exists | `/opt/fpai/aria-command/.env` | Metered |
| xAI | ✅ key exists | `/opt/fpai/ai-brain/api_keys.env` | Metered |
| Mem0 | ✅ key exists | `/opt/fpai/aria-command/.env` | Memory service |
| Meta/Facebook | ⚠️ expired | `/opt/fpai/api_keys.json` | Needs refresh from James |

---

## Python Libraries (server 162, system Python)

| Library | Version | What it enables |
|---|---|---|
| `playwright` | 1.58.0 | Headless browser (Chromium verified working) |
| `twilio` | 9.10.0 | SMS / voice |
| `openai-whisper` | 20240930 | Local voice transcription ($0) |
| `openai` | 1.12.0 | OpenAI API client |
| `anthropic` | 0.18.1 | Anthropic API client |
| `python-telegram-bot` | 20.7 | Telegram bot |
| `fastapi` + `uvicorn` | 0.109/0.27 | HTTP API server |
| `aiohttp` | 3.13.2 | Async HTTP |
| `requests` | 2.32.5 | HTTP client |
| `psycopg` | 3.3.3 | PostgreSQL async |

**Curator venv** (`/opt/sh-brain-src/.venv/`): psycopg, psycopg-binary + curator packages.

---

## Running Applications (Docker) — server 162

| App | Port | What it does |
|---|---|---|
| **n8n** | localhost:5678 | Workflow automation — ALREADY RUNNING |
| **Firefly III** | localhost:18280 | Personal finance manager |
| **Paperless-ngx** | localhost:18180 | Document management |
| **AppFlowy** (2 instances) | internal | Collaborative workspace (appflowy-cloud + sh-brain) |
| sh-brain (AppFlowy) | internal | James's brain workspace |

---

## Running Applications — server 198

| App/Service | Status | What it does |
|---|---|---|
| **Evolution API** (WhatsApp) | ✅ live | WhatsApp send/receive, webhook to port 8774 |
| Champion-sign | ✅ running | Game champion signing service |
| FP Game Bot | ✅ running | Telegram bot for the Full Potential Game |
| Concierge suite (15 services) | ✅ running | AI concierge platform (leads, voice, outbound, skills, knowledge) |
| Nerve Center | ✅ running | Central coordination |
| Whaletrack | ✅ running | Financial tracking |
| Revenue Oracle | ✅ running | Revenue tracking |
| Legal Guardian | ✅ running | Legal AI service |
| Voice Phone | ✅ running | Voice capabilities on 198 |
| FP Index | ✅ running | Content indexing |
| Proactive Monitor | ✅ running | Proactive outreach monitor |
| Postfix + Dovecot | ✅ running | Mail server (MX for fullpotential.ai etc) |

---

## Node.js CLI Tools (server 162, global)

| Tool | What it does |
|---|---|
| `claude-code` (v2.1.181) | Claude Code CLI — used by build loop |
| `codex` (v0.139.0) | OpenAI Codex CLI — $0 via subscription |
| `openclaw` | Custom CLI tool |
| `clawdhub` | Custom hub tool |

---

## Databases

| DB | Host | Notes |
|---|---|---|
| brain_index (PostgreSQL) | 162, localhost | Live CRM: probe_pool, probe_sessions, corrections, thread, decisions, becoming |
| AppFlowy Postgres (pgvector) | 162, Docker | Vector-enabled, 2 instances |
| Firefly MariaDB | 162, Docker | Finance data |
| Paperless Postgres | 162, Docker | Document metadata |
| Redis | 162, Docker + 198 | Cache/queues |

### brain_index active tables
`probe_pool` · `probe_sessions` · `probe_reply_queue` · `corrections` · `thread` · `decisions` · `becoming` · `contact_profiles` (d080)

---

## Autonomous Loops (server 162)

| Loop | Timer | What it does | Kill switch |
|---|---|---|---|
| Build loop | every 10min | spec→codex→claude -p review→TG | `touch /opt/fpai-build/.disabled` |
| IMAP poller | every 2min | poll sunheartai inbox → probe handler | `systemctl stop fpai-imap-poller.timer` |
| Council debate | every 5min | 3-lens debate → propose build → TG | `~/.config/fpai/council/.disabled` |
| Morning digest | 08:00 Athens | daily summary → Telegram | `.digest_disabled` |

---

## Gaps (what's actually missing)

| Resource | Why needed | Cost |
|---|---|---|
| 2captcha key | CAPTCHA solving for browser signup flows | ~$2 deposit |
| Tavily / Exa key | Real-time web search for contact discovery | Free tier |
| Hunter.io key | Email discovery from name/domain | Free: 25/mo |
| Fresh Meta token | Instagram/Facebook posting | James re-auths once |
| ElevenLabs key | Realistic voice replies | Free → $11/mo |
| Mastodon account | Federated social presence | $0 — autonomous today |
| WhatsApp number connected | Evolution API is live but needs a WA number scanned | James scans QR once |

---

## Cost Constraints

- **$20/day hard ceiling** on all metered API usage
- **Subscription-first**: `claude -p` + `codex` = $0 marginal
- **Local-first**: Ollama (T1) before any API call
- **RunPod**: $50/month ceiling
- **Twilio**: $14.15 balance — replenish when below $5
