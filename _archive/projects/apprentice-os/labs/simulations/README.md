# Simulations Lab

> Test system behavior safely with synthetic data.

## Purpose

Before connecting real humans to the system, validate all rules and workflows 
using synthetic data.

- Test decision engine rules safely
- Validate n8n workflow triggers
- Ensure shadow cost calculations work as expected
- Train Full Potential on edge cases without emotional stakes

## Convention

All simulation data is tagged:

- Events: `event_type` prefixed with `sim.` (e.g., `sim.metric.updated`)
- Apprentices: `name` prefixed with `[SIM]`
- System state: `simulation_mode = true` flag set

## Structure

```
/simulations
├── /scenarios        # Test scenario definitions
│   ├── coherence-drop.yaml
│   ├── fragile-loop.yaml
│   ├── successful-loop.yaml
│   └── complexity-creep.yaml
├── /data-generators  # Scripts to create synthetic data
│   └── fake-metrics.py
└── README.md
```

## Running Simulations

1. Set `simulation_mode = true` in system_state
2. Run scenario script (creates synthetic apprentice, pumps metrics)
3. Observe: Does Full Potential surface the right alerts? Do workflows trigger?
4. Validate: Check events table for expected `sim.*` events
5. Reset: Clear simulation data, set `simulation_mode = false`

## Planned Scenarios

### coherence-drop.yaml
Simulates steward coherence falling below baseline.
Expected: System pauses expansion, alerts steward.

### fragile-loop.yaml
Simulates apprentice showing stress + trust decay.
Expected: Loop flagged as potentially extractive.

### successful-loop.yaml
Simulates apprentice progressing well.
Expected: Resources amplified, oversight reduced.

### complexity-creep.yaml
Simulates system approaching complexity threshold.
Expected: Warning at 1.2x, block at 1.5x.

---

*Simulations let us test the system without risking real relationships.*


