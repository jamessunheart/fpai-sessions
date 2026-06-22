# Codex build result — SPEC_d021_memory-rag-bridge-via-git-post
_ran: 2026-06-16T00:05:25Z · branch: build/SPEC_d021_memory-rag-bridge-via-git-post_

## Summary
Built the memory-git to RAG bridge for the Sunheart Brain stack. The bridge adds:

- an authenticated `/index/ingest/memory_git_note` endpoint that reuses the existing `embed()` pipeline and upserts directly into `brain_index.note_chunks`;
- idempotent schema support for `source_path`, `commit_sha`, and `updated_at`;
- a post-commit hook wrapper plus `memory_git_bridge.py` helper for `/opt/fpai-build/memory`;
- local filtering for `.md` files only, secret/private path exclusions, and the existing ingest privacy classifier before any network write.

## Files Changed
- `SERVICES/sunheart-brain/index/ingest_routes.py`
- `SERVICES/sunheart-brain/index/schema.sql`
- `SERVICES/sunheart-brain/ingest/memory_git_bridge.py`
- `SERVICES/sunheart-brain/ingest/hooks/memory-post-commit`
- `SERVICES/sunheart-brain/ingest/test_memory_git_bridge.py`
- `SERVICES/sunheart-brain/runbook/deploy.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d021_memory-rag-bridge-via-git-post.md`
- `core/BUILD/results/SPEC_d021_memory-rag-bridge-via-git-post.result.md`
- `docs/codex/HANDOFF.md`

## Tests
- `python3 -B -m unittest SERVICES/sunheart-brain/ingest/test_memory_git_bridge.py` — 4 tests OK.
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/ingest/memory_git_bridge.py SERVICES/sunheart-brain/ingest/test_memory_git_bridge.py SERVICES/sunheart-brain/index/ingest_routes.py` — OK.
- `git diff --check -- SERVICES/sunheart-brain/index/schema.sql SERVICES/sunheart-brain/index/ingest_routes.py SERVICES/sunheart-brain/ingest/memory_git_bridge.py SERVICES/sunheart-brain/ingest/hooks/memory-post-commit SERVICES/sunheart-brain/ingest/test_memory_git_bridge.py SERVICES/sunheart-brain/runbook/deploy.md core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d021_memory-rag-bridge-via-git-post.md core/BUILD/results/SPEC_d021_memory-rag-bridge-via-git-post.result.md docs/codex/HANDOFF.md` — OK.

## Risks
- This sandbox did not SSH to server 162, install the live hook, restart the brain-index service, or perform the end-to-end phone-Ember proof against production RAG.
- The hook requires `SH_INGEST_TOKEN` in its runtime environment and the deployed script path at `SH_MEMORY_GIT_BRIDGE` or `/opt/sh-brain-src/ingest/memory_git_bridge.py`.
- Path/content filtering is conservative but not a substitute for James/Ember keeping secrets out of the git-backed memory SSOT.

## Rollback
Remove `/opt/fpai-build/memory/.git/hooks/post-commit` on server 162 and revert the changed repo files. Remove bridge-ingested rows with:

```sql
DELETE FROM brain_index.note_chunks WHERE source_path LIKE 'memory-git/%';
```

## Intent Solved
Git-backed flat-file memory can now flow into the semantic RAG index after commits without manual re-ingest.

## Downstream Intent Unlocked
Phone/SSH memory edits can become queryable by Ember after one post-commit cycle, closing the remaining SSOT-to-RAG island once deployed on server 162.
