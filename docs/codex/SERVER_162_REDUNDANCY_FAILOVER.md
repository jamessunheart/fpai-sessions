# Server 162 Redundancy And Failover Plan

Repo-side plan for the secondary Brain host `162.0.208.88`. This document is
based on checked-in repo evidence and the read-only inventory captured in
`infra/audits/inventory_2026-04-30_1246/`. It does not prove current live state
after that inventory date, and it does not authorize SSH, DNS changes, deploys,
service stops, money movement, or secret handling.

## Evidence Scope

| Source | What it proves | Limit |
|---|---|---|
| `infra/audits/inventory_2026-04-30_1246/SUMMARY.md` | Cross-server host roles, secondary resource profile, docker/systemd overview, and cross-server dependencies. | Snapshot from 2026-04-30. |
| `infra/audits/inventory_2026-04-30_1246/secondary_162.0.208.88.txt` | Running services, listening ports, nginx `server_name`, docker containers, cron entries, and Tailscale address at snapshot time. | Not a live heartbeat. |
| `docs/codex/HOST_REGISTRY.md` | Host truth confidence is still partial and report-only. | No L2 heartbeat coverage. |
| `docs/codex/SERVICE_REGISTRY.md` | Repo-local service classifications and deployment hints. | Generated from repo metadata, not live process truth. |
| `SERVICES/sunheart-brain/README.md` | Intended Brain architecture, deployment path, DNS target, MCP/index/AppFlowy components. | Under-construction service docs. |
| `SERVICES/streasury-bot/README.md` | STreasury host, port, database dependency, deploy flow, and systemd unit. | README says Phase 1 scaffold; live use may differ. |

## Dependency Map

| Layer | Dependency on `162.0.208.88` | Evidence | Failure impact if 162 is down |
|---|---|---|---|
| Host identity | Ubuntu 22.04 secondary host, 31 GiB RAM, 437G root disk, Tailscale `100.127.118.106`, public IP `162.0.208.88`. | Inventory `IDENTITY`, `RAM`, `DISK`, listening ports. | All Brain/secondary services unreachable; Tailscale-only management path lost unless provider console works. |
| Public ingress | nginx serves `triad.fullpotential.ai` and the bare IP; Sunheart Brain docs expect `brain.sunheart.com` A record to `162.0.208.88`. | Inventory nginx list; `SERVICES/sunheart-brain/README.md`. | DNS names and direct-IP clients fail until DNS/proxy points at replacement. |
| Brain memory stack | `sh-brain` docker stack: nginx, AppFlowy Cloud, worker, GoTrue, pgvector Postgres, MinIO, Redis, appflowy web/admin. Host services `sh-brain-index`, `sh-mcp-http`, `sh-brain-tgbot`. | Inventory docker/systemd; Sunheart Brain README/compose. | MCP memory, semantic search, Telegram Brain bot, and cross-tool memory bridge stop. |
| Zen/AppFlowy sibling stack | AppFlowy Cloud docker stack separate from `sh-brain`; prior handoff references Zen Village morning digest and gotrue auth. | Inventory docker list; handoff open questions. | Zen/AppFlowy-backed surfaces, digest auth, and stored workspace data may be unavailable. |
| Financial/document/workflow apps | Firefly III + MariaDB, Paperless-ngx + Postgres + Redis, n8n, MinIO. | Inventory docker list. | Financial tracking, document access, and workflow automation stop unless volumes/backups are restored. |
| Local model and AI routing | Ollama on port `11434`; `ai-brain.service` on `8101`; `reasoning-engine` on `8140`; `fpai-ai-gateway`, `gpu-bridge`, `kai-bridge`, `memory-bus`. | Inventory services/ports; hardcoded URL scan. | Any code using local inference, AI provider brain, or secondary GPU/bridge routes fails or falls back poorly. |
| STreasury | `streasury-bot.service` on port `8620`; DB schema `streasury` in `sh-brain-postgres` exposed on `127.0.0.1:25432`; Outbounders read-only DB allowlist permits `162.0.208.88`. | STreasury README and inventory handoff. | Treasury bot/reports and Outbounders revenue sync stop; replacement host needs DB restore and legacy DB allowlist update. |
| Build/proof timers | Review artifacts target server 162 for preference export, intent protocol extractor, horizon scanner, probe agent, blueprint auditor, tool scout, agent benchmarking, smoke/spec checks. | `core/BUILD/cron/*`, `core/BUILD/systemd/*`, build results. | Autonomous review/reporting jobs stop; missing rows may make handoff and proof surfaces stale. |
| Cross-server monitoring | Secondary cron includes `/opt/fpai/scripts/monitor-primary.sh`; earlier cockpit pattern has primary polling secondary and legacy. | Inventory root cron and handoff. | Fleet status becomes incomplete; primary/legacy may still run but central visibility degrades. |

## Hardcoded IP Inventory

These repo-visible references should be moved behind DNS names or environment
variables before failover is considered tested. Some are defaults and can be
overridden; they still matter because a cold redeploy often starts from defaults.
The scan intentionally excludes `_archive/`, virtualenvs, and the historical
`infra/audits/` snapshot from this active-risk table; those sources remain
evidence, not current remediation scope.

| Path | Hardcoded value | Current role | Failover action |
|---|---|---|---|
| `SERVICES/ad-portal/app/config.py`; `SERVICES/ad-portal/docker-compose.yml` | `AI_BRAIN_URL=http://162.0.208.88:8101` | Ad portal AI generation/config points directly at AI Brain. | Require env override and set to AI Brain alias. |
| `SERVICES/aria/app/main.py`; `SERVICES/aria-bridge/proactive.py`; `SERVICES/aria-bridge/manifestation.py` | `_DEFAULT_SECONDARY_IP` / `SECONDARY_SERVER` = `162.0.208.88` | Aria/bridge secondary routing. | Use Host Registry alias, not public IP. |
| `SERVICES/aria/app/gpu_control.py`; `SERVICES/aria/core/router.py`; `SERVICES/aria/core/sensors/infrastructure.py` | GPU bridge/scaler/Ollama URLs on `162.0.208.88` | GPU/local model routing. | Alias `gpu-bridge.internal`, `ollama.internal`, `smart-scaler.internal`. |
| `SERVICES/aria/core/digest.py`; `SERVICES/aria/core/proactive.py`; `SERVICES/aria/core/approvals.py`; `SERVICES/aria/core/curiosity.py` | Multiple direct health/status/notify URLs on `162.0.208.88` | Aria digest/proactive/status paths. | Centralize secondary endpoints in config. |
| `SERVICES/aria/aria.service`; `SERVICES/aria/deploy.sh`; `SERVICES/aria-builder/deploy.sh`; `SERVICES/aria-bridge/deploy.sh` | Service env/deploy target `162.0.208.88` | Server-side Aria deployment. | Replace with deployment alias; keep direct IP only in emergency runbook. |
| `SERVICES/aria/brain_client_new.py`; `SERVICES/aria-bridge/translator.py` | AI Brain/Ollama defaults on `162.0.208.88` | Aria AI/local inference clients. | Require env alias defaults. |
| `SERVICES/aria-command/access/filesystem.py`; `SERVICES/aria-command/access/terminal.py`; `SERVICES/aria-command/ops/server_ops.py` | Secondary host `162.0.208.88` | Aria command server access abstractions. | Route through Host Registry and approval gates. |
| `SERVICES/aria-command/agents/registry.py` | Agent endpoints `http://162.0.208.88:8710/health`, `:8720/health` | Agent registry health endpoints. | Use per-agent aliases. |
| `SERVICES/aria-command/brain/opus_brain.py`; `SERVICES/aria-command/deploy.sh`; `SERVICES/aria-command/builder/unified_engine.py`; `SERVICES/aria-command/knowledge/money_systems.py` | Runtime/deploy knowledge of secondary `162.0.208.88` | Aria command deployment and money-system URL generation. | Move host facts into Host Registry/config. |
| `SERVICES/aria-command/consciousness/optimizer_bridge.py` | `CONSCIOUSNESS_OPTIMIZER_HOST` default `162.0.208.88` | Consciousness optimizer bridge. | Alias `consciousness-optimizer.internal`. |
| `SERVICES/aria-command/integrations/n8n_client.py` | `N8N_URL` default `http://162.0.208.88:5678` | n8n integration. | Alias `n8n.internal`; verify replacement n8n data restore before enablement. |
| `SERVICES/aria-command/intelligence/config_contracts.py`; `SERVICES/aria-command/intelligence/root_cause.py`; `SERVICES/aria-command/intelligence/real_verification.py` | AI Brain/Aria/secondary verification URLs on `162.0.208.88` | Health/config verification logic. | Replace IP assertions with alias/registry checks. |
| `SERVICES/aria-command/proactive/digest.py`; `SERVICES/aria-command/proactive/monitors.py`; `SERVICES/aria-command/proactive/server_watchdog.py` | Secondary host and service health URLs on `162.0.208.88` | Proactive monitoring. | Use alias map and make old IP a degraded finding. |
| `SERVICES/aria-command/telegram/bot.py` | `http://162.0.208.88:8101/ask` | Telegram bot AI Brain calls. | Route via AI Brain alias. |
| `SERVICES/aria-command/sovereign/agents/monitor.py` | `SECONDARY_SERVER = "162.0.208.88"` | Server/service health checks. | Rename to `BRAIN_SERVER_HOST`; default to DNS/Tailscale alias. |
| `SERVICES/aria-command/sovereign/workflows/actions.py` | Secondary SSH host `162.0.208.88` | Restart, memory cleanup, command execution. | Gate or disable live SSH actions; use host registry alias after approval. |
| `SERVICES/autonomous-income-engine/main.py`; `SERVICES/god-autonomous-revenue/main.py`; `SERVICES/nerve_center/server.py` | AI Brain defaults on `162.0.208.88:8101` | Revenue/autonomy/nerve-center AI calls. | Require `AI_BRAIN_URL` alias and fail closed if unset in prod. |
| `SERVICES/chief-of-staff/app/digest.py`; `SERVICES/chief-of-staff/daily_briefing.py`; `SERVICES/chief-of-staff/deploy.sh`; `SERVICES/chief-of-staff/scripts/deploy.sh` | STreasury/brain/deploy URLs on `162.0.208.88` | Chief-of-staff digest and deployment. | Alias STreasury/brain endpoints and deployment target. |
| `SERVICES/consciousness_optimizer/app/optimizer.py` | `http://162.0.208.88:8230`, `:8240` | Consciousness verifier/feeder optimization loop. | Alias verifier/feeder endpoints; keep disabled until replacement health proof. |
| `SERVICES/data-service/app/main.py`; `SERVICES/data-service/app/prophet.py`; `SERVICES/reasoning-engine/app/main.py`; `SERVICES/intelligence-core/app/learning.py` | AI Brain/data-service URLs on `162.0.208.88` | Data/reasoning/learning service calls. | Alias `ai-brain.internal` and `data-service.internal`. |
| `SERVICES/fp-index/app/signal_router.py` | `AI_BRAIN_URL` default `http://162.0.208.88:8101` | Provider routing checks AI Brain directly. | Replace default with `http://brain.internal:8101` or require `AI_BRAIN_URL`; document env in deploy. |
| `SERVICES/fp-index/app/engine.py`; `SERVICES/fp-index/app/actuators.py`; `SERVICES/fp-index/app/autonomous_actions.py`; `SERVICES/fp-index/docker-compose.yml` | AI Brain/Sparket URLs on `162.0.208.88` | FP Index generation, actuators, autonomous actions. | Route through env aliases and freeze actuators during failover. |
| `SERVICES/fp-credits-gateway/app/main.py`; `SERVICES/fp-credits-gateway/app/static/purchase.html` | AI Brain/user service direct URLs on `162.0.208.88` | Credits gateway AI/user service calls and browser JS. | Backend alias plus public-safe API proxy; remove browser direct IP. |
| `SERVICES/god-mode/backend/main.py` | Consciousness/AI/Aria direct URLs on `162.0.208.88` | God-mode service dependencies. | Alias and keep write-capable features disabled until approved. |
| `SERVICES/gpu-manager/config.py`; `SERVICES/gpu-manager/README.md`; `SERVICES/gpu-smart-scaler/smart_scaler.py`; `SERVICES/gpu_watchdog.py` | GPU bridge/AI Brain/notify URLs on `162.0.208.88` | GPU operations and docs. | Alias GPU bridge/manager and confirm no autonomous spend during failover. |
| `SERVICES/i-match/app/matching_engine.py`; `SERVICES/jsservers-bot/bot.py`; `SERVICES/proactive-monitor/app/monitor.py` | AI Brain/secondary service defaults on `162.0.208.88` | Product/service clients that reach Brain host. | Alias AI/secondary endpoints; update public-facing links if any. |
| `SERVICES/social-auto-poster/run_pipeline.sh`; `SERVICES/social-auto-poster/SPEC.md` | SSH to `root@162.0.208.88` | Content pipeline server hook. | Disable during failover unless explicitly approved; replace with alias. |
| `SERVICES/streasury-bot/scripts/deploy.sh`; `SERVICES/streasury-bot/scripts/quickstart.sh`; `SERVICES/streasury-bot/runbook/*`; `SERVICES/streasury-bot/README.md` | STreasury host/deploy references `162.0.208.88` | Treasury bot deployment and operator docs. | Update after alias/restore drill; replacement needs DB restore first. |
| `SERVICES/sunheart-brain/README.md`; `SERVICES/sunheart-brain/runbook/*`; `SERVICES/sunheart-brain/scripts/*`; `SERVICES/sunheart-brain/ingest/*.sh`; `SERVICES/sunheart-brain/schema/build_schema.py`; `SERVICES/sunheart-brain/nginx/brain.sunheart.com.conf` | Brain host, SSH, DNS, ingest sync target `162.0.208.88` | Core Brain deployment/docs/ingest. | Replace with `brain.sunheart.com`/Tailscale alias after live restore proof. |
| `SERVICES/zen-village/app/cockpit_hub.py`; `docs/zen-village/runbook/*`; `docs/zen-village/telegram/README.md`; `docs/zen-village/deploy_log.yaml`; `docs/zen-village/workflows/parser_ollama_prompt.md` | Brain/secondary/Ollama URLs and SSH/DNS targets on `162.0.208.88` | Zen Village brain, digest, backups, parser, accounting docs. | Alias Ollama/brain; verify backup sync and digest after restore. |
| `SERVICES/legal-critic/deploy.sh`; `SERVICES/legal-critic/README.md` | `LEGAL_CRITIC_HOST` default `root@162.0.208.88` | Legal critic deploy and hosted legal critique docs. | Alias deploy host; keep legal surface disabled until restored and reviewed. |
| `SERVICES/concierge/shared/config.py` | `ai_brain_url = "http://162.0.208.88:8101"` | Concierge stack talks to AI Brain. | Use env-only or DNS alias such as `https://ai-brain.fullpotential.ai`/Tailscale name. |
| `SERVICES/zend-wallet/app/config.py` | `AI_BRAIN_URL = "http://162.0.208.88:8101"` | Zend wallet fallback direct AI call. | Require `ZEND_AI_BRAIN_URL` and set to failover alias. |
| `SERVICES/deploy-droplet.sh` | `root@100.127.118.106` | Tailscale deploy target for secondary. | Keep as private failover path only if replacement joins Tailscale with a stable MagicDNS name. |
| `tools/council/debate.py`; `tools/decisions/feed_decision.sh`; `tools/decisions/bridge_to_codex.sh`; `tools/merge/process_merge_requests.sh` | `BRAIN_HOST` default `root@162.0.208.88` | Council, decision routing, Codex build dispatch, and merge-request processing. | Use host alias; fail closed if Brain host is unavailable rather than losing decision/merge truth. |
| `tools/decisions/mirror_pull.py`; `tools/decisions/scene_pull.py` | `SERVER = "root@162.0.208.88"` | Pulls Brain digest and scene state from server 162 into local/vault mirrors. | Alias Brain host and record stale mirror warning during outage. |
| `tools/memory/tg_brain_bridge.sh`; `tools/memory/patch_brain_memory.py`; `tools/memory/treasury_to_brain.py` | Brain SSH target `root@162.0.208.88` | Telegram Brain memory bridge and memory patch/sync helpers. | Alias Brain host; disable bridge writes until restored source of truth is selected. |
| `tools/decisions/ember_responder_prompt.md` | Operator prompt includes direct SSH command to `162.0.208.88` | Human/Ember runbook command memory. | Update after alias migration so operator prompts do not reintroduce the IP. |
| `tools/cartographer/build_index.py` | SSH inventory target includes `162.0.208.88` | Fleet inventory docs. | Regenerate from Host Registry aliases. |
| `docs/deployment/CONSCIOUSNESS_SERVICES_DEPLOYMENT.md` | `root@162.0.208.88`, direct curl URLs | Historical deployment guide. | Update after host aliasing so future docs do not reintroduce the IP. |
| `docs/coordination/SSOT.json` | AI inference, Ollama, GPU bridge on `162.0.208.88` | Older coordination state. | Treat as stale until regenerated from Host Registry. |
| `docs/ADAM_ARCHITECTURE.md`; `infra/adam-workspace-patches/*` | Adam/OpenClaw secondary identity on `162.0.208.88` | Adam substrate docs/patches. | Re-home Adam only after Brain replacement is proven. |
| `docs/architecture/*`; `docs/business/INCOME_NOW.md`; `docs/HOW_IT_WORKS.md`; `docs/UNIFIED_INTELLIGENCE_ARCHITECTURE.md`; `core/INTELLIGENCE/*`; `core/STATE/*`; `core/INTENT/*` | Multiple maps and proof notes mention direct 162 URLs. | Historical/canonical memory surfaces and architecture docs. | Regenerate/annotate after alias migration; do not treat historical proofs as deploy commands. |
| `infra/audits/inventory_2026-04-30_1246/HANDOFF.md` | Legacy DB allowlist `streasury_ro@'162.0.208.88'` | Outbounders revenue sync source restriction. | On failover, add replacement host to legacy allowlist before enabling sync. |
| `infra/audits/inventory_2026-04-30_1246/secondary_162.0.208.88.txt` | nginx `server_name triad.fullpotential.ai 162.0.208.88` | Historical live nginx state. | Replacement nginx should serve names only; direct IP is for emergency diagnostics. |

## Recovery Objectives

| Surface | Target RTO | Target RPO | Reason |
|---|---:|---:|---|
| `@sunheartbrain_bot`, MCP/index, Brain search | 4 hours | 24 hours until backup proof improves | James-facing memory and routing degrade quickly. |
| STreasury bot and sync | 8 hours | 24 hours for Postgres schema; 30 minutes for sync if source replay works | Financial visibility matters, but no autonomous money movement is allowed. |
| AppFlowy/MinIO/Paperless/Firefly/n8n | 24 hours | 24 hours | Useful operational data; restore after Brain/treasury path. |
| Local Ollama/AI Brain fallback | 24 hours | Stateless except model cache/config | Can temporarily degrade to paid APIs if budget gate allows. |
| Review/proof timers | 24 hours | Missed timers can be rerun manually | Staleness is visible but not immediately catastrophic. |

## Redundancy Design

1. **Introduce stable aliases before moving anything.** Use DNS/Tailscale names
   such as `brain.internal`, `ai-brain.internal`, `ollama.internal`,
   `streasury.internal`, and public names for browser-facing surfaces. Direct IPs
   should not be application defaults.
2. **Back up state daily off-host.** Minimum set: `sh-brain-postgres`,
   AppFlowy/Postgres volumes, MinIO buckets, STreasury schema, Firefly DB,
   Paperless DB/media, n8n data, `/etc/nginx/sites-enabled`, relevant systemd
   units, `/etc/*/*.env` secret filenames/checksums only, and cron definitions.
   Do not commit secrets.
3. **Keep a warm standby recipe, not a mystery server.** A replacement host
   should be reproducible from repo artifacts plus encrypted/off-repo secrets:
   Ubuntu 22.04+, Docker, compose, nginx, certbot, Tailscale, Python 3.11,
   system users, restored volumes, and enabled systemd units.
4. **Separate data restore from service enablement.** Restore volumes and run
   health checks first; only then switch DNS/aliases and enable timers.
5. **Fail closed on spend and irreversible actions.** During failover, disable or
   keep paused any service that can spend money, send outreach, trade, deploy, or
   mutate public state until James/Ember explicitly approves that exact action.

## If 162 Goes Down

### Phase 0 - Confirm And Freeze

1. Confirm outage from at least two paths: public HTTPS/DNS, Tailscale/MagicDNS,
   and provider console if available.
2. Freeze nonessential automation by keeping review/probe/build timers disabled
   on the replacement until data restore and health checks pass.
3. Record outage start time and last known good backup timestamp in HANDOFF.
4. Do not rotate secrets, alter DNS, or touch legacy allowlists until the restore
   host is selected and James/Ember has approved the cutover.

### Phase 1 - Select Replacement Host

Preferred order:

1. New low-privilege Brain replacement host, same OS family and disk class.
2. Primary `198.54.123.234` as temporary app-only bridge for Brain APIs if it has
   enough RAM after pausing noncritical services.
3. Legacy `209.74.93.72` only for Outbounders/cPanel continuity, not as default
   Brain replacement.

Provision baseline:

```bash
apt-get update
apt-get install -y docker.io docker-compose-plugin nginx certbot python3.11 python3.11-venv tailscale postgresql-client rsync
usermod -aG docker root
tailscale up
```

### Phase 2 - Restore Data

Restore in this order:

1. `sh-brain-postgres` and `sh-brain-minio` volumes.
2. AppFlowy sibling stack Postgres/MinIO volumes.
3. STreasury schema and `/opt/streasury-bot` source.
4. Firefly, Paperless, and n8n volumes/databases.
5. nginx vhosts and certbot state, or issue new certs after DNS points to the
   replacement.

Verification before public cutover:

```bash
docker compose -p sh-brain ps
curl -fsS http://127.0.0.1:28080/ || true
curl -fsS http://127.0.0.1:28090/health
curl -fsS http://127.0.0.1:28091/health
curl -fsS http://127.0.0.1:8620/health
curl -fsS http://127.0.0.1:8101/health
```

### Phase 3 - Repoint Aliases

1. Move public DNS names to the replacement only after local health checks pass.
2. Move internal aliases/Tailscale names used by services.
3. Update legacy MariaDB allowlist for Outbounders sync from the replacement host
   IP, then verify `streasury-sync` in dry-run/report mode first.
4. Update environment files to alias names, not direct IPs.
5. Start user-facing services first, then reporting timers, then probes/scanners.

### Phase 4 - Redeploy Services

Recommended order:

1. `sh-brain` docker compose and `sh-brain-index`/`sh-mcp-http`.
2. `sh-brain-tgbot` with Telegram send disabled or owner-only smoke mode.
3. `streasury-bot` and `streasury-sync` after DB restore.
4. AppFlowy sibling stack, Firefly, Paperless, n8n.
5. AI Brain, reasoning engine, Ollama, GPU bridge, kai bridge.
6. Review/proof timers under `core/BUILD/cron` and `core/BUILD/systemd`.

### Phase 5 - Proof

Required proof before declaring failover complete:

1. `@sunheartbrain_bot` responds to an owner-only health command.
2. MCP search returns a known non-secret fixture/concept.
3. STreasury `/health` returns OK and report-only sync can read Outbounders.
4. `AI_BRAIN_URL` clients hit the alias, not `162.0.208.88`.
5. `rg '162\\.0\\.208\\.88'` remaining hits are either historical docs, this
   plan, or explicit compatibility notes.
6. HANDOFF records what was restored, backup timestamp, tests, gaps, and rollback.

## Pre-Failover Work Queue

| Priority | Work | Owner lane |
|---|---|---|
| P0 | Add live-safe heartbeat spec for Host Registry so L2 status is current before outages. | Codex spec + Ember live host run. |
| P0 | Replace direct `162.0.208.88` app defaults with env-required aliases in active services. | Codex, one approved code spec. |
| P0 | Create off-host backup manifest and restore drill for `sh-brain`, STreasury, AppFlowy, Firefly, Paperless, n8n. | Ember/live ops; Codex can write repo scripts if specced. |
| P1 | Document exact volume paths and backup destinations from the live host. | Ember/live host. |
| P1 | Add replacement-host bootstrap script that installs packages but does not copy secrets or start services. | Codex. |
| P1 | Run a tabletop drill using a temporary host or local containers. | Ember + Codex proof. |

## Rollback

If failover cutover misbehaves:

1. Repoint DNS/aliases back to `162.0.208.88` only if the original host is healthy.
2. Stop replacement services that might duplicate writes: Telegram bots, sync
   timers, n8n workflows, probes/scanners.
3. Preserve replacement logs and restored volume snapshots for comparison.
4. Re-run owner-only health checks on the original host.
5. Record the failed cutover in HANDOFF before another attempt.

## Open Gaps

- No current L2 heartbeat exists in the repo; this is a plan from L0/L1 evidence.
- Exact backup locations, cadence, and restore success for each docker volume are
  not proven.
- Secret material names are known by role but not available here, correctly.
- Current DNS provider state was not queried.
- Current live service state after 2026-04-30 was not probed because this run is
  repo-only and no SSH/network action was approved.

## Intent Proof

```text
Intent solved: server 162 has a dependency map, hardcoded-IP inventory, and failover sequence instead of being an implicit single point of failure.
Downstream intent unlocked: James/Ember can approve a narrow live heartbeat/backup-restore drill without asking Codex to rediscover the stack.
Proof: this document names the stack, dependencies, hardcoded defaults, recovery order, gates, tests, rollback, and open gaps.
Next unlocked move: route a P0 code spec to replace active direct-IP defaults with aliases, then a live-host restore drill spec.
```
