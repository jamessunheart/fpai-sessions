# Mission: Activate Treasury (M001)

- **Priority:** P0
- **Status:** Ready for Owner Input
- **Owner:** Treasury Operator
- **Constitution Principle:** **Optimization over Extraction** — every trade should expand shared capital rather than drain reserves.
- **Regenerative Impact:** Magnet simulation unlocks safe treasury growth experiments that can fund human + AI relief missions.
- **Objective:** Prime Magnet trading stack with Binance testnet keys and confirm vault automation.
- **Files/Systems:** `droplets/hteam/droplet-3/`, `infra/secrets.vault.example.json`, `orchestration/tools/inject_vault.py`, `/opt/fpai/env/magnet.env`
- **Dependencies:** Registry + Orchestrator live, secrets vault template ready.

## Required Actions
1. Copy `infra/secrets.vault.example.json` to `infra/secrets.vault.json` locally.
2. Insert Binance testnet API key/secret plus Redis URL.
3. Run `python orchestration/tools/inject_vault.py --target magnet` to populate `/opt/fpai/env/magnet.env`.
4. Signal ops to move Magnet to staging once env file is populated.

## Notes
- Do **not** commit `secrets.vault.json`.
- Confirm `/opt/fpai/env/magnet.env` permission stays `600`.
- Contact ops if registry JWT rotates; both registry + orchestrator must share the new value.
