# AI Review — build/SPEC_d050_module-blueprint-system-living-c

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Adds a config-gated, fail-safe (|| true, BLUEPRINTS_DISABLE) post-merge blueprint-regen hook to the live 162 build loop — no money/secrets/main/push touched, but it injects an untested, up-to-180s synchronous `claude -p` call into the merge path, a real stall risk for a loop with recent stall history.

## Findings
- Stall risk on the live server-162 build loop: `update_blueprint_after_merge` makes a SYNCHRONOUS call to `manager.py update-after-build`, which runs `claude -p --effort high` with a 180s timeout (manager.py:208-216) and no shell-level timeout/backgrounding. It fires after EVERY merge — including inside the backlog `while read` loop (server_build_loop.sh:242), so N backlog merges = up to N×180s of blocking. The build loop's own recent history is stall-fixing (befb973 stall detection, 3aac0f9 drained 26 stuck worktrees); inserting an up-to-3-min blocking external call into the merge path reintroduces exactly that failure mode. The author's own result.md notes a `claude -p` review attempt just timed out at 90s. Fix: wrap with `timeout 60` and/or background the call so it can never block the merge pass.
- Untested against live state by the author's own admission: result.md says live post-merge regeneration was never exercised against real `claude -p`, git commit behavior, or server-162 build-loop state, and the independent review gate for this delta was NOT passed (claude -p timed out). This is the first review pass.
- Mid-loop `git commit` (manager.py:289-300): the hook calls `update-after-build` WITHOUT `--no-commit`, so each merge triggers a `git add <blueprint path>` + `git commit` on feat/headless-build. Scoping to the single blueprint path avoids sweeping unrelated dirty files (good), but adds uncommitted-state coupling to the live loop that wasn't proven safe in sandbox. Note: no push and no main-branch write — that part is safe.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
