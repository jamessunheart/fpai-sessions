# Buildstream — ranked by leverage (Compass · d005)

Produced 2026-06-14 from the 5 answered decisions. Per d005, James approves the
ranking before anything runs. Each item is the `proof_expected` of a decision he made.

| Rank | Build | From | Leverage | Risk | Artifact |
|------|-------|------|----------|------|----------|
| 1 | **Instrument Rack — model routing** | d003 ✅ | High — every AI action routes through it | Low (local yaml) | `core/STATE/INSTRUMENT_RACK.yaml` |
| 2 | **Healer — safe auto-fix policy** | d001 ✅ | High — unlocks bounded self-healing | Low (policy doc first; executor later, gated) | `core/STATE/policies/HEALER_POLICY.md` |
| 3 | **Council Fire — debate config** | d002 ✅ | Medium — fires only on big/irreversible calls | Low (config; $1 cap) | `core/STATE/COUNCIL_FIRE.yaml` |
| 4 | **Self-feed the queue** | (loop-closer) | High — recursive_improver → feed_decision.sh | Low-Med (laptop wire) | wire existing scripts |
| — | Comms Hub | d004 ✅ | — | — | **no build — decided to keep iterating** |

## Notes
- 1–3 are local, reversible config/policy files — within the d001 "reversible safe-auto" bound James just approved.
- 4 is the highest-leverage *loop-closer* (makes the queue feed itself) but wasn't a decision — flagged for explicit ok.
- Healer's **executor** (code that actually auto-restarts services) stays gated — policy doc first, execution only after a second explicit go.
