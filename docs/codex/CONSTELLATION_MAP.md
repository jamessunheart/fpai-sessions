# CONSTELLATION MAP — the 14 command functions (repo mirror)

Canonical James-readable version: vault `00_MEMORY/CONSTELLATION MAP.md`.
This mirror exists so phone/cloud Codex sessions can use the vocabulary without iCloud.
Adopted as canonical naming 2026-06-10 (James). Status: 9 🟢 built · 5 🟡 partial · 0 empty.

| # | Function | Does | Status | Machinery (repo-side) |
|---|----------|------|--------|----------------------|
| 1 | Compass | choose direction | 🟢 | vault HOME via `tools/decisions/daily_sync.py` · `core/STATE/NOW.md` · INTENT_BUILDSTREAM |
| 2 | Lantern | notice reality, weak signals | 🟡 | narrator · freshness (inward); `tools/scout/scout_run.py` installed, FAIL-CLOSED until SCOUT_MODEL_CMD provider configured — flips 🟢 on first live run evidence |
| 3 | Maproom | know the terrain | 🟢 | `tools/index/refresh.py` · SERVER/fleet maps · cartographer |
| 4 | Gate | protect the field | 🟢 | `core/STATE/RESERVED_CLASS.yaml` · `tools/reserved/classify.py` · cost cap · hooks |
| 5 | Bridge | any signal → intent | 🟡 | `tools/queue/verb_router.py` · tg inbox · qb; full hub = Rung 4 (`spec comms`) |
| 6 | Forge | build what matters | 🟢 | Claude/Codex/apprentice fleet · the-forge |
| 7 | Mirror | reveal what happened | 🟢 | PROOF LOG · true-narrator · `tools/consequence/` · STATE_STATUS |
| 8 | Root | remember & grow | 🟢 | memory stack · BRICKs · brain server · vault 00_MEMORY |
| 9 | Watchfire | guard the system itself | 🟢 | `tools/vault/freshness.py` · `tools/state_reconciler/` · email canary · cost ledger |
| 10 | Healer | repair & restore | 🟡 | freshness `--heal` (allowlist) · `reverse.sh`; widen by proof |
| 11 | Council Fire | multi-perspective judgment | 🟡 | debate-decide-log · cross-substrate auditor; needs auto-convene rule |
| 12 | Instrument Rack | right model/tool per job | 🟡 | `tools/router/route.py` · pipeline routing.yaml; partial coverage |
| 13 | Proof River | evidence flows back | 🟢 | PROOF LOG · `proofs/` · proof-commit discipline |
| 14 | Loop | close the loop, compound | 🟢 | autoloop 2h · daily_sync · SETTLE · recursive-optimizer |

Naming convention going forward: new machinery declares which function it serves
(commit messages + specs may use e.g. `watchfire:` / `bridge:` prefixes or mention the room).
Gap queue (leverage order): Bridge → Lantern → Council Fire → Instrument Rack → Healer.
