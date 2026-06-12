---
generated: true
source: tools/registry/build.py
last_generated: 2026-06-05 17:06 UTC
edit_policy: regenerate, do not hand-edit
---

# Service Registry / World Map

Read-only map of `SERVICES/*`. This report never stops, deletes, archives, deploys, or mutates a service.

## Summary

- Services directory entries scanned: **127**
- Registry rows written: **127**
- Status counts: archived: 75 · live: 16 · paused: 2 · ❓ needs-human-classify: 34
- Safety: report only; cleanup requires a separate James-approved spec.
- Redaction: raw IPs and secret-like env values are redacted in extracted hints.

## Classification Rules

- `live`: systemd unit present or touched within 45 days.
- `paused`: no unit, touched within 46-180 days, or metadata says pause.
- `archived`: no unit and stale beyond 180 days, or metadata says archive/retire.
- `❓ needs-human-classify`: template/special directory or missing recency signal.

## Obvious Retire-Candidates

- `email-dashboard` — 201d stale; reason: stale 201d
- `sol-treasury-ssot` — 201d stale; reason: stale 201d
- `task-automation` — 201d stale; reason: stale 201d
- `webmail` — 201d stale; reason: stale 201d
- `worthy-recipient` — 201d stale; reason: stale 201d
- `2x-treasury` — 195d stale; reason: stale 195d
- `api-hub` — 195d stale; reason: stale 195d
- `approval-dashboard` — 195d stale; reason: stale 195d
- `autonomous-agents` — 195d stale; reason: stale 195d
- `autonomous-execution-engine` — 195d stale; reason: stale 195d
- `build-executor` — 195d stale; reason: stale 195d
- `collective-mind` — 195d stale; reason: stale 195d
- `companion-claude` — 195d stale; reason: stale 195d
- `content-generation-engine` — 195d stale; reason: stale 195d
- `contribution-bridge` — 195d stale; reason: stale 195d
- `coordination-hub` — 195d stale; reason: stale 195d
- `coranation` — 195d stale; reason: stale 195d
- `email-automation-system` — 195d stale; reason: stale 195d
- `fpai-hub` — 195d stale; reason: stale 195d
- `governance` — 195d stale; reason: stale 195d
- `hub` — 195d stale; reason: stale 195d
- `i-match-automation` — 195d stale; reason: metadata says archive/retire
- `integration` — 195d stale; reason: stale 195d
- `intent-queue` — 195d stale; reason: stale 195d
- `kubernetes` — 195d stale; reason: stale 195d

## Registry

| Service | Status | Last touched | Systemd unit | URL/deploy target | Cost hint | Kill condition | Notes |
|---|---|---:|---|---|---|---|---|
| `2x-treasury` | archived | 2025-11-21 | no | — | — | — | stale 195d; readme:README.md |
| `_TEMPLATE` | ❓ needs-human-classify | 2025-11-21 | no | **URL**: https://fullpotential.com/[service-path] | — | — | template/special directory; readme:README.md |
| `ad-portal` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `admin-gate` | archived | 2025-11-25 | no | — | — | — | stale 191d |
| `admin-hub` | archived | 2025-11-29 | no | — | — | — | stale 188d |
| `ai-automation` | archived | 2025-11-23 | no | Server runs on: `http://localhost:8700` | **Goal:** Generate $20-30k/month recurring revenue through productized AI automation services | — | stale 193d; readme:README_OLD.md |
| `alignment-economics` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `api-gateway` | archived | 2025-11-29 | no | — | — | — | stale 188d |
| `api-hub` | archived | 2025-11-21 | no | — | - ✅ **Image Generation:** Stable Diffusion (FREE), DALL-E 3 ($0.04/img) | — | stale 195d; readme:README.md |
| `api-portal` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `apprentice-gateway` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `apprentice-studio` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `approval-dashboard` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `aria` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `aria-command` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `auto-fix-engine` | archived | 2025-11-25 | no | # Expose the port the app runs on | EXPOSE ${PORT} | — | stale 191d; readme:README.md, Dockerfile |
| `autonomous-agents` | archived | 2025-11-21 | no | ### **Deploy First Agent (5 minutes):** | python3 agents/monitoring_agent.py | — | stale 195d; readme:README.md |
| `autonomous-execution-engine` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `autonomous-executor` | archived | 2025-11-25 | no | # Deploys manually... | — | — | stale 191d; readme:README.md, Dockerfile |
| `autonomous-income-engine` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `autonomy-optimizer` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `becoming-page` | live | 2026-05-19 | no | — | — | — | touched 16d ago |
| `brain-mesh-gateway` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `brick2-marketing-engine` | live | 2025-11-29 | yes: SERVICES/brick2-marketing-engine/deploy/autopilot.service | uvicorn app.main:app --reload --port 8700 | \| ≤$8/hr \| 5.00% \| | — | systemd unit present; readme:README.md |
| `build-executor` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `champion-sign` | live | 2026-05-08 | yes: SERVICES/champion-sign/champion-sign.service | — | — | — | systemd unit present |
| `chief-of-staff` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `church-guidance-ministry` | archived | 2025-11-23 | no | **Production URL:** http://[redacted-ip]:8009 | — | — | stale 193d; readme:README.md |
| `collective-mind` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `communication-hub` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `companion-claude` | archived | 2025-11-21 | no | Access at: `http://localhost:8900/director` | - Financial metrics (treasury, revenue, costs) | — | stale 195d; readme:README.md |
| `concierge` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `consciousness_feeder` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `content-generation-engine` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `content-studio` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `contribution-bridge` | archived | 2025-11-21 | no | │ • Security report │ | - Small: $10-50 (0.1-0.3 SOL) | — | stale 195d; readme:README.md |
| `coordination-hub` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `coranation` | archived | 2025-11-21 | no | Server runs on: `http://localhost:8900` | proxy_set_header Host $host; | — | stale 195d; readme:README.md |
| `credentials-manager` | archived | 2025-11-25 | no | # Expose the port the app runs on | EXPOSE ${PORT} | — | stale 191d; readme:README.md, Dockerfile |
| `dashboard` | archived | 2025-11-23 | no | uvicorn app.main:app --reload --port 8002 | — | — | stale 193d; readme:README.md, Dockerfile |
| `data-service` | paused | 2025-12-13 | no | — | — | — | touched 173d ago |
| `deployer` | archived | 2025-11-25 | no | # Deployer needs more permissions often, but we start restricted | EXPOSE ${PORT} | — | stale 191d; readme:README.md, Dockerfile |
| `email-automation-system` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `email-dashboard` | archived | 2025-11-15 | no | — | — | — | stale 201d |
| `ember-substrate-mcp` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `fp-credits-gateway` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `fp-game-bot` | live | 2026-05-08 | yes: SERVICES/fp-game-bot/fp-game-bot.service | — | — | — | systemd unit present |
| `fp-index` | live | 2026-05-08 | no | - AI_BRAIN_URL=http://[redacted-ip]:8101 | ### Metered Tools (cost credits) | — | touched 28d ago; readme:README.md, docker-compose, Dockerfile |
| `fpai-hub` | archived | 2025-11-21 | no | - Homepage: http://localhost:8010 | - `GET /api/token/metrics` - Token supply, backing, price | — | stale 195d; readme:README.md |
| `global-sky-initiative` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `god-autonomous-revenue` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `god-mode` | archived | 2025-11-26 | no | — | — | — | stale 191d; docker-compose |
| `governance` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `gpu-manager` | live | 2026-05-18 | yes: SERVICES/gpu-manager/gpu-manager.service | export VASTAI_API_KEY=[redacted] | A **UNIFIED** GPU management system that replaces the broken dual-system (GPU Hunter + GPU Watc… | — | systemd unit present; readme:README.md, Dockerfile |
| `gpu-smart-scaler` | live | 2026-05-18 | no | — | — | — | touched 17d ago |
| `harvester` | live | 2025-11-26 | yes: SERVICES/harvester/harvester.service | — | — | — | systemd unit present |
| `helper-management` | archived | 2025-11-25 | no | # Expose the port the app runs on | EXPOSE ${PORT} | — | stale 191d; readme:README.md, Dockerfile |
| `hub` | archived | 2025-11-21 | no | Server runs on: `http://localhost:8500` | proxy_set_header Host $host; | — | stale 195d; readme:README.md |
| `i-match` | archived | 2025-12-13 | no | uvicorn app.main:app --reload --port 8401 | - **Month 1**: $40-150K (20-50 matches) | "needs_description": "Looking for a financial advisor to help with retirement planning and tax… | metadata says archive/retire; readme:README.md, Dockerfile |
| `i-match-automation` | archived | 2025-11-21 | no | **Web interface at http://localhost:8510** | — | "specialty": "retirement planning" | metadata says archive/retire; readme:README.md |
| `i-proactive` | paused | 2025-12-13 | no | - Specialized agents: Strategist, Builder, Optimizer, Deployer, Analyzer | - Build cost vs revenue analysis | — | touched 173d ago; readme:README.md, Dockerfile |
| `integration` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `intent-queue` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `jobs` | archived | 2025-11-25 | no | CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8008/health')" | TOKEN=[redacted] -X POST http://registry:8000/auth/token \ | — | stale 191d; readme:README.md, Dockerfile |
| `kubernetes` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `landing-page` | archived | 2025-11-29 | no | - DASHBOARD_API=http://[redacted-ip]:8002/api | — | — | stale 188d; readme:README.md, docker-compose, Dockerfile |
| `legal` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `legal-critic` | live | 2026-05-11 | no | export BRAIN_INGEST_TOKEN=[redacted] | — | — | touched 24d ago; readme:README.md |
| `legal-verification-agent` | archived | 2025-11-21 | no | uvicorn src.main:app --host [redacted-ip] --port 8010 --reload | — | — | stale 195d; readme:README.md |
| `marketing` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `master-dashboard` | archived | 2025-11-25 | no | — | — | — | stale 191d |
| `membership` | archived | 2025-11-21 | no | — | — | — | stale 195d; readme:README.md |
| `memory-curator` | archived | 2026-05-12 | no | — | - **Cost:** zero — pure local computation, no API calls | - **Pin/archive markers** in the description (`[pin]` = top, `[archive]` = bottom) | metadata says archive/retire; readme:README.md |
| `mission-control` | live | 2025-11-29 | yes: SERVICES/mission-control/mission-control.service | "repo_url": "https://github.com/user/repo", # optional | — | — | systemd unit present; readme:README.md |
| `mission-hub` | archived | 2025-11-29 | no | ### Harvester (Port 8055) | — | — | stale 188d; readme:README.md |
| `mydreamspace` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `nerve_center` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `nexus-event-bus` | archived | 2025-11-23 | no | uvicorn main:app --host [redacted-ip] --port 8450 --reload | — | — | stale 193d; readme:README.md |
| `ops` | archived | 2025-11-21 | no | - Deployment automation | — | — | stale 195d; readme:README.md |
| `orchestrator` | archived | 2025-11-21 | no | test: ["CMD", "curl", "-f", "http://localhost:8000/health"] | — | — | stale 195d; readme:README.md, docker-compose, Dockerfile |
| `orchestrator-unified` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `outbounders-integration` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `outbounders-script-gen` | live | 2026-05-23 | no | - **Hosting**: Cloudflare Pages + Workers (free tier) OR Vercel Edge Function | - **Backend**: Cloudflare Worker calling Anthropic Claude API (Haiku for cost) — `worker/index.… | — | touched 12d ago; readme:README.md |
| `phase1-execution-engine` | archived | 2025-11-23 | no | — | — | — | stale 193d |
| `proactive-monitor` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `proof-witness` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `proxy-manager` | archived | 2025-11-25 | no | — | — | — | stale 191d; Dockerfile |
| `reddit-auto-responder` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `registry` | archived | 2025-11-23 | no | CMD curl -f http://localhost:8000/health \|\| exit 1 | — | — | stale 193d; readme:README.md, Dockerfile |
| `revenue-intelligence` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `seo-landing-generator` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `service-discovery` | archived | 2025-11-23 | no | — | — | — | stale 193d |
| `service-registry-monitor` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `sessions-api` | live | 2026-05-08 | yes: SERVICES/sessions-api/sessions-api.service | — | — | — | systemd unit present |
| `social-auto-poster` | live | 2026-05-19 | no | — | — | — | touched 16d ago |
| `sol-treasury-ssot` | archived | 2025-11-16 | no | — | - Treasury Manager ($400K DeFi) | — | stale 201d; readme:README.md |
| `sovereign-factory` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `spec-builder` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `spec-optimizer` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `spec-verifier` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `strategic-intelligence` | archived | 2025-11-23 | no | — | — | — | stale 193d |
| `streasury-bot` | archived | 2026-05-08 | yes: SERVICES/streasury-bot/systemd/streasury-bot.service | > **One conversation, every number.** Telegram bot at [@STreasury_Bot](https://t.me/STreasury_B… | psql "$DATABASE_URL" -f schema/streasury_schema.sql | \| `/accounts add stripe USD` \| Create or archive accounts. \| | metadata says archive/retire; readme:README.md, python |
| `sunheart-ai-page` | live | 2026-05-27 | no | — | — | — | touched 8d ago |
| `sunheart-brain` | live | 2026-05-09 | yes: SERVICES/sunheart-brain/scripts/sh-brain-index.service, SERVICES/sunheart-brain/scripts/sh-mcp-… | **Status:** under construction (see `docs/zen-village/deploy_log.yaml` for the | — | — | systemd unit present; readme:README.md |
| `task-automation` | archived | 2025-11-15 | no | export ANTHROPIC_API_KEY=[redacted] | — | — | stale 201d; readme:README.md |
| `team-hub` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `test-compliance-demo` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `TIE-SYSTEM` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `token` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `treasury` | archived | 2025-11-23 | no | — | — | — | stale 193d |
| `treasury-arena` | archived | 2025-11-21 | no | ## 🚀 Build & Deployment Plan | **Capital Target:** $210K (56% of treasury) | — | stale 195d; readme:README.md |
| `treasury-dashboard` | archived | 2025-11-21 | no | Dashboard available at: http://localhost:8005/dashboard | **Real-time visualization of the $373K → $5 Trillion journey** | — | stale 195d; readme:README.md |
| `treasury-manager` | archived | 2025-11-23 | no | "deploy:sepolia": "hardhat run scripts/deploy.js --network sepolia", | **Intelligent DeFi portfolio management system managing $400K with AI-driven decision making** | — | stale 193d; readme:README.md |
| `unified-assembly-line` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `unified-chat` | archived | 2025-11-23 | no | ### **Step 1: Deploy the Chat Server** | — | — | stale 193d; readme:README.md |
| `unified-financial-dashboard` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `verifier` | archived | 2025-11-25 | no | uvicorn app.main:app --reload --port 8008 | — | — | stale 191d; readme:README.md, Dockerfile |
| `voice-phone` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `webmail` | archived | 2025-11-15 | no | — | — | — | stale 201d |
| `wellness-optimizer` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `white-rock-landing` | archived | 2025-11-21 | no | — | — | — | stale 195d |
| `worthy-recipient` | archived | 2025-11-16 | no | - Higher monthly support = higher score | - Fix James's old Mercedes ($8K from treasury) | — | stale 201d; readme:README.md |
| `zen-village` | live | 2026-05-30 | no | — | — | — | touched 6d ago |
| `zend-marketplace` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `zend-ton` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `zend-wallet` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
| `zv-wallet` | ❓ needs-human-classify | ❓ no git signal | no | — | — | — | no git recency signal |
