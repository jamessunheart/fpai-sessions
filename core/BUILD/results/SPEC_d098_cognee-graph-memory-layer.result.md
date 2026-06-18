# SPEC d098 — Cognee Graph Memory Layer Result

## Status

Done in working tree. Not pushed, merged, deployed, or activated live.

## Files Changed

- `SERVICES/sunheart-brain/index/schema.sql`
- `SERVICES/sunheart-brain/curator/graph_memory.py`
- `SERVICES/sunheart-brain/curator/test_graph_memory.py`
- `core/BUILD/specs/SPEC_d098_cognee-graph-memory-layer.md`
- `core/BUILD/results/SPEC_d098_cognee-graph-memory-layer.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added an additive graph memory layer over existing `brain_index` rows. The new schema adds `graph_memory_nodes`, `graph_memory_edges`, and `graph_memory_runs` tables for relationship traversal without replacing `note_chunks`, `probe_pool`, `becoming`, or `corrections`.

Added `curator/graph_memory.py`, which reads a 10-contact proof slice from `probe_pool`, joins available `becoming` stages, normalizes topics such as `regenerative cities`, writes idempotent graph nodes/edges, and records a query proof row. The runtime default is Postgres; if `COGNEE_GRAPH_BACKEND=cognee` is set and the Cognee package is installed, the sync is tagged for Cognee-backed operation while preserving the same normalized graph records.

## Proof

- Indexes 10 probe contacts into person/topic/becoming-stage graph records.
- Query shape `who is connected to regenerative cities?` resolves to the `regenerative-cities` topic and returns Josh plus related contacts in tests.
- Rehydration test proves graph relationships survive a serialize/reload boundary, matching the “preserved across sessions” proof target at repo level.

## Tests

```text
python3 -B -m unittest SERVICES/sunheart-brain/curator/test_graph_memory.py
python3 -B -m unittest SERVICES/sunheart-brain/curator/test_becoming.py SERVICES/sunheart-brain/curator/test_graph_memory.py
env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/graph_memory.py SERVICES/sunheart-brain/curator/test_graph_memory.py
python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d098-registry.json
git diff --check
```

## Commit

Attempted local `git add ... && git commit`; blocked because Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d098_cognee-graph-memory-layer/index.lock` on the read-only shared Git metadata.

## Risks

- Live Cognee package installation and live DB sync were not run in the sandbox.
- `probe_pool` metadata is semi-structured, so topic extraction is conservative and may need tuning after observing live rows.
- The graph layer is advisory memory traversal, not an outreach trigger, approval, diagnosis, or replacement for existing memory tables.

## Rollback

Revert the listed files. If schema was applied live and a full rollback is required, export wanted proof rows first, then drop `brain_index.graph_memory_edges`, `brain_index.graph_memory_nodes`, and `brain_index.graph_memory_runs`.

## Intent Solved

`brain_index` now has an additive relationship graph layer so contacts, becoming stages, interests, proofs, and corrections can be traversed as graph memory rather than isolated rows.

## Downstream Intent Unlocked

Ember can run one live d098 proof on server 162: sync 10 real `probe_pool` contacts, query “who is connected to regenerative cities?”, confirm Josh plus related contacts return, and confirm the query remains available after a fresh process/session.
