# Coherence Score

classification: COUNCIL-OPEN
privacy: repo-surface synthesis only; no secrets, private messages, or external scans
generated_by: d103 coherence weekly score
generated_at: 2026-06-18T19:33:24Z
status: PASS
score: 98.1/100

## Components

- source_coverage: 100.0%
- voice_signal_coverage: 100.0%
- freshness: 100.0%
- drift_penalty: 87.5%
- registry_hygiene: 100.0%

## Source Signals

- docs/codex/AI_PROTOCOLS.md: exists=True; age=0.0d; signals=source, routing, proof, memory, safety, next_intent; drift=none
- docs/codex/INTENT_BUILDSTREAM.md: exists=True; age=0.0d; signals=source, routing, proof, memory, safety, next_intent; drift=none
- docs/codex/HANDOFF.md: exists=True; age=0.0d; signals=source, routing, proof, memory, safety, next_intent; drift=none
- docs/codex/ATTENTION_FLOW.md: exists=True; age=0.0d; signals=source, routing, proof, memory, safety, next_intent; drift=none
- core/STATE/NORTH_STAR.md: exists=True; age=0.0d; signals=source, routing, proof, memory, safety; drift=none
- core/STATE/SELF_PORTRAIT.md: exists=True; age=0.0d; signals=source, routing, proof, memory, safety; drift=none
- core/STATE/HOT_STATE.md: exists=True; age=0.0d; signals=source, routing, proof, memory, next_intent; drift=stale_surface
- core/STATE/MODEL_DNA.md: exists=True; age=0.0d; signals=source, routing, proof; drift=none

## Registry Gaps

- none

## Recommended Repairs

- Review drift flags before the next autonomous run: core/STATE/HOT_STATE.md (stale_surface)
