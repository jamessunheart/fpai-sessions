# Mission: Magnet Trading Testnet Keys

- **Status:** Open
- **Priority:** P1
- **Human Role:** Treasury Ops partner with Binance Testnet access (no production secrets)
- **Linked Specs:**
  - `core/applications/magnet-trading-system/DEPLOYMENT_PLAN.md`
  - `docs/library/coordination/missions/mission-002-linkedin-launch.json` (for reporting cadence)

## Objective
Provision Binance testnet API keys and wire them into the Magnet Trading backend so the survival fuse + strategy simulators can run end-to-end.

## Scope & Files
- https://testnet.binance.vision/ (account + API management)
- Local repo path: `core/applications/magnet-trading-system/backend/.env`

## Steps
1. Log into Binance Testnet and create an API key/secret (testnet only).
2. On your workstation, run:
   ```bash
   cd /Users/jamessunheart/Development/fullpotential_ai/fullpotential_core/core/applications/magnet-trading-system/backend
   cp .env.example .env   # if needed
   ```
3. Populate the variables `BINANCE_API_KEY` and `BINANCE_API_SECRET` with the testnet values (store locally; do **not** commit).
4. Run health checks:
   ```bash
   uvicorn api.main:app --port 8025 &
   curl http://localhost:8025/health
   curl http://localhost:8025/api/fuse/status
   ```
5. Capture the JSON output and stop the server.

## Deliverable
- Health responses pasted into `missions.md` (Magnet Trading row) or linked gist.
- Confirmation that `.env` remains local/untracked.

## Review Log
| Date | Reviewer | Notes |
| --- | --- | --- |
