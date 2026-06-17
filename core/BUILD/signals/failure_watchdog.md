# Proactive Failure Watchdog Report

**Generated:** 2026-06-17T00:09:17Z
**Mode:** report-only local scan; no SSH, deploy, service restart, spend, outreach, or secret access.

## Summary

- Total findings: 7
- Max severity: 5
- P0 findings: 0
- P1 findings: 5
- P2 findings: 2

| Category | Findings |
|---|---:|
| server | 2 |
| memory | 1 |
| revenue | 1 |
| agents | 0 |
| dependencies | 3 |

## Findings

### server · severity 5 · Direct host/IP dependencies remain in active repo surfaces
- **Detail:** Direct IP or localhost endpoint references make failover dependent on manual edits or exact host topology.
- **Next action:** Replace active direct-IP defaults with named aliases or env-driven endpoints, then re-run d059 failover proof.
- **Evidence:**
  - `tools/outbounders_revenue_pull.sh: 209.74.93.72`
  - `tools/deploy_game.sh: 198.54.123.234`
  - `tools/memory/treasury_to_brain.py: 162.0.208.88`
  - `tools/memory/tg_brain_bridge.sh: 162.0.208.88`
  - `tools/memory/patch_brain_memory.py: 162.0.208.88`
  - `tools/command_center/build_dashboard.py: 198.54.123.234`
  - `tools/merge/process_merge_requests.sh: 162.0.208.88`
  - `tools/zen_village_scorer/sync_applications.py: 198.54.123.234`
  - `tools/decisions/scene_pull.py: 162.0.208.88`
  - `tools/decisions/ember_responder_prompt.md: 162.0.208.88, 198.54.123.234, 209.74.93.72`
  - `tools/decisions/mirror_pull.py: 162.0.208.88`
  - `tools/decisions/bridge_to_codex.sh: 162.0.208.88`

### server · severity 4 · Host heartbeat coverage is not proved
- **Detail:** The host registry still separates repo metadata from live heartbeat truth, so server death may be noticed late.
- **Next action:** Run or build the read-only live heartbeat proof from an approved host lane.
- **Evidence:**
  - `docs/codex/HOST_REGISTRY.md has no live heartbeat coverage`

### revenue · severity 4 · Revenue surfaces contain direct endpoint dependencies
- **Detail:** Revenue-related paths still reference concrete host endpoints, which can break income flow when a server moves.
- **Next action:** Move revenue endpoints behind env vars or host aliases and add a live heartbeat check.
- **Evidence:**
  - `tools/outbounders_revenue_pull.sh: 209.74.93.72`
  - `tools/memory/treasury_to_brain.py: 162.0.208.88`
  - `scripts/activate-revenue-streams.sh: 162.0.208.88:8101, 198.54.123.234:8401, 198.54.123.234:8600, 198.54.123.234:8750, 198.54.123.234:8765`
  - `SERVICES/REVENUE_SYSTEM_READY.md: 198.54.123.234:8005, 198.54.123.234:8009, 198.54.123.234:8020, 198.54.123.234:8401`
  - `SERVICES/REVENUE_OPTIMIZATION_PLAN.md: 198.54.123.234:8005, 198.54.123.234:8009, 198.54.123.234:8020`
  - `SERVICES/2x-treasury/AI_RECRUITMENT_READY.md: 198.54.123.234:8052`
  - `SERVICES/2x-treasury/LAUNCH_SUMMARY.md: 198.54.123.234:8052`
  - `SERVICES/2x-treasury/ai_recruiter.py: 198.54.123.234:8052`
  - `SERVICES/2x-treasury/deploy.sh: 198.54.123.234, 198.54.123.234:8052`
  - `SERVICES/2x-treasury/SUSTAINABLE_PROOF_PLAN.md: 198.54.123.234:8052`
  - `SERVICES/chief-of-staff/scripts/refresh_revenue.sh: 127.0.0.1:8770, 198.54.123.234, 198.54.123.234:8770`
  - `SERVICES/chief-of-staff/scripts/refresh_outbounders.sh: 209.74.93.72`

### memory · severity 4 · No recent smoke-test proof in ops ledger
- **Detail:** Memory and pipeline canary checks may be absent from the regular proof stream.
- **Next action:** Install/verify the d049 smoke-test timer or run one silent smoke proof from the live host.
- **Evidence:**
  - `/opt/fpai-build/ops_ledger.jsonl`

### dependencies · severity 4 · Conflicting pinned dependency versions exist
- **Detail:** Different services pin the same package to different versions, increasing deploy/restore drift risk.
- **Next action:** Create a reviewed dependency BOM for live services and reconcile conflicts service by service.
- **Evidence:**
  - `aiofiles: 23.2.1, 24.1.0`
  - `aiohttp: 3.9.0, 3.9.1`
  - `alembic: 1.12.1, 1.13.0, 1.13.1, 1.13.3`
  - `anthropic: 0.18.1, 0.39.0, 0.7.0, 0.7.7, 0.7.8`
  - `asyncpg: 0.29.0, 0.30.0`
  - `beautifulsoup4: 4.12.2, 4.12.3`
  - `celery: 5.3.4, 5.3.6`
  - `fastapi: 0.104.1, 0.109.0, 0.115.0, 0.115.5`
  - `httpx: 0.25.0, 0.25.1, 0.25.2, 0.26.0, 0.27.0, 0.27.2, 0.28.0`
  - `jinja2: 3.1.2, 3.1.3`
  - `pandas: 2.1.3, 2.1.4`
  - `pydantic: 2.10.0, 2.10.3, 2.4.0, 2.4.2, 2.5.0, 2.5.2, 2.6.4, 2.9.0, 2.9.2`

### dependencies · severity 3 · Many dependencies are unpinned or floating
- **Detail:** 86 dependency entries have no explicit fixed version.
- **Next action:** For live services, pin direct dependencies or record why floating versions are acceptable.
- **Evidence:**
  - `SERVICES/ad-portal/frontend/package.json: react@^18.2.0`
  - `SERVICES/ad-portal/frontend/package.json: react-dom@^18.2.0`
  - `SERVICES/ad-portal/frontend/package.json: react-router-dom@^6.20.0`
  - `SERVICES/ad-portal/frontend/package.json: @tanstack/react-query@^5.8.0`
  - `SERVICES/ad-portal/frontend/package.json: recharts@^2.10.0`
  - `SERVICES/ad-portal/frontend/package.json: axios@^1.6.0`
  - `SERVICES/ad-portal/frontend/package.json: date-fns@^2.30.0`
  - `SERVICES/ad-portal/frontend/package.json: lucide-react@^0.294.0`
  - `SERVICES/ad-portal/frontend/package.json: clsx@^2.0.0`
  - `SERVICES/ad-portal/frontend/package.json: @types/react@^18.2.0`
  - `SERVICES/ad-portal/frontend/package.json: @types/react-dom@^18.2.0`
  - `SERVICES/ad-portal/frontend/package.json: @vitejs/plugin-react@^4.2.0`

### dependencies · severity 3 · Large dependency surface spans many service manifests
- **Detail:** 115 requirement/package manifests are present across the repo.
- **Next action:** Prioritize a dependency BOM/lock audit for live services before broad service activation.
- **Evidence:**
  - `DASHBOARDS/master/requirements.txt`
  - `PRODUCTS/crypto-portfolio-tracker/requirements.txt`
  - `SERVICES/2x-treasury/requirements.txt`
  - `SERVICES/TIE-SYSTEM/governance-guardian/requirements.txt`
  - `SERVICES/TIE-SYSTEM/integration-tests/requirements.txt`
  - `SERVICES/TIE-SYSTEM/sol-treasury-core/requirements.txt`
  - `SERVICES/TIE-SYSTEM/tie-contract-manager/requirements.txt`
  - `SERVICES/TIE-SYSTEM/voting-weight-tracker/requirements.txt`
  - `SERVICES/ad-portal/frontend/package.json`
  - `SERVICES/ad-portal/requirements.txt`
  - `SERVICES/admin-gate/requirements.txt`
  - `SERVICES/admin-hub/requirements.txt`
