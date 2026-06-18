# SPEC_d104_attention-engine-relevance-trigg Result

## Status

Done in working tree. Not pushed, not merged, no live deploy.

## Summary

Added relevance-triggered attention surfacing on top of the existing brain-index
pgvector search path. Telegram brain search now carries note provenance
(`note_row_id`, `chunk_idx`) from `brain_index.note_chunks`, filters current
pgvector hits through a bounded attention helper, and injects only high-scoring
public/personal candidates into the synthesis prompt as advisory context.

Added `brain_index.attention_surface_events` as append-only proof that a current
query surfaced candidates. The logger is best-effort and never blocks chat
answers. No scheduled checker, timer, sender, approval path, or proactive
message was added.

## Files Changed

- `SERVICES/sunheart-brain/curator/attention.py`
- `SERVICES/sunheart-brain/curator/test_attention.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `SERVICES/sunheart-brain/index/schema.sql`
- `core/BUILD/specs/SPEC_d104_attention-engine-relevance-trigg.md`
- `core/BUILD/results/SPEC_d104_attention-engine-relevance-trigg.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_attention.py'` — 4 tests OK
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_tgbot_correction_wiring.py'` — 4 tests OK
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_bot_mode_gate.py'` — 5 tests OK
- `env HOT_MEMORY_STATE_PATH=/tmp/nonexistent-d104-hot-state.md SELF_DIAGNOSTIC_CONTEXT_FILE=/tmp/nonexistent-d104-diagnostic.json python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_build_context.py'` — 9 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/attention.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_attention.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d104-registry.json`
- `git diff --check`

Ambient note: `test_build_context.py` fails on this host without env isolation
because a live diagnostic context and fresh `HOT_STATE.md` cause the hot-state
branch to replace fixture repo context. With those ambient paths redirected, the
test suite passes.

## Risks

- Live DB migration was not applied in this sandbox; the new audit table appears
  when `SERVICES/sunheart-brain/index/schema.sql` is applied by the brain-index
  service.
- Attention candidates are heuristic thresholded pgvector hits. They should be
  treated as advisory context, not truth, approval, or reminder obligations.
- If live indexed chunks lack useful tags, surfacing still works by cosine score
  but has less explainable ranking.

## Rollback

Revert the d104 files listed above. Runtime rollback without reverting code:
set `SH_ATTENTION_SURFACING_DISABLE=1` to stop prompt surfacing, or
`SH_ATTENTION_LOG_DISABLE=1` to stop audit writes. If the schema was applied and
a full rollback is desired, drop `brain_index.attention_surface_events` after
exporting any wanted proof rows.

## Intent

Intent solved: current conversations can surface relevant memory by similarity
when it matters, instead of relying on scheduled reminder/check passes.

Downstream intent unlocked: the attention engine can be expanded into richer
event-triggered surfaces using live relevance evidence and audit rows, without
adding proactive sends or James-facing scheduled noise.
