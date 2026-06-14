# SPEC_build-registry-and-merge-gate

*System-wide build routing and integration protocol. Prevents parallel Codex sessions from
stomping each other, rogue pushes to main, and merge conflicts. Owner: Ember (gate) + Codex (builds).*

## The problem
Multiple Codex sessions build in parallel on the same repo. Without coordination:
- Sessions push conflicting commits to the same branch
- Sessions open PRs to `main` instead of `feat/headless-build`
- No one knows what's actively being built or by whom
- Ember resolves conflicts manually every merge

## The three-layer fix

### Layer 1 — Build Registry (`core/BUILD/REGISTRY.json`)
Single file every build session reads at start and writes at done. Ember owns this file.

**Schema:**
```json
{
  "schema": "build-registry.v1",
  "updated_at": "<ISO UTC>",
  "active_builds": [
    {
      "id": "build-<YYYYMMDD>-<slug>",
      "slug": "<what-is-being-built>",
      "branch": "codex/<slug>",
      "base_branch": "feat/headless-build",
      "session": "<codex-session-id or description>",
      "status": "building | done | merged | cancelled",
      "started_at": "<ISO UTC>",
      "spec": "docs/codex/specs/SPEC_<slug>.md",
      "tests_passed": null,
      "pr_number": null,
      "notes": ""
    }
  ]
}
```

**Rules:**
- Every Codex session registers its build here before writing any code
- Status transitions: `building → done → merged` (only Ember sets `merged`)
- Two builds with the same `slug` cannot both be `building` simultaneously
- Ember checks this file before merging any PR

### Layer 2 — Codex Session Contract (`docs/codex/SESSION_CONTRACT.md`)
One-page rules every Codex session must follow. Paste at session start.

**The contract:**
```
CODEX BUILD CONTRACT — read before writing any code.

1. BRANCH: always branch off feat/headless-build. Never branch off main.
   git checkout feat/headless-build && git pull && git checkout -b codex/<slug>

2. REGISTER: before writing code, add your build to core/BUILD/REGISTRY.json (status: building).

3. BUILD: write code, run tests, commit locally. Do NOT push. Do NOT open PRs.

4. DONE: when tests pass, set status: done in REGISTRY.json. Commit that change.
   Tell James: "Done. Branch: codex/<slug>. Tests: N passed. Waiting for merge."

5. NEVER: push to main. Open PRs to main. Force-push. Touch secrets. Auto-deploy.
   Ember handles all pushes, PR creation, and merges.
```

### Layer 3 — Ember Merge Gate (`tools/merge/merge_gate.sh`)
Script Ember runs before merging any PR. Checks:
1. PR base branch is `feat/headless-build` (not `main`)
2. Branch exists in REGISTRY.json with `status: done`
3. Tests pass on the branch
4. No conflicts with current `feat/headless-build` HEAD
5. Only then: merge, update REGISTRY.json `status: merged`, pull locally

## Definition of Done

### 1. `core/BUILD/REGISTRY.json` — created, schema above, empty `active_builds: []`

### 2. `docs/codex/SESSION_CONTRACT.md` — the contract above, formatted for paste

### 3. `tools/merge/merge_gate.sh <branch>` — script that:
- Checks branch exists locally or on remote
- Checks `core/BUILD/REGISTRY.json` for matching entry with `status: done`
- Runs `python3 -m pytest` scoped to the changed SERVICES directory
- Prints PASS or FAIL with reason
- On PASS: prints the `gh pr merge` command to run (does NOT run it — Ember confirms)
- On FAIL: prints what failed, exits non-zero

### 4. `tools/merge/test_merge_gate.sh` — tests:
- Branch in registry with `status: done` → PASS
- Branch not in registry → FAIL with "not registered"
- Branch in registry with `status: building` → FAIL with "still building"
- Tests fail → FAIL with test output

### 5. Update `docs/codex/HANDOFF.md` — add section:
```
## Build Protocol (required reading)
Before writing any code: read docs/codex/SESSION_CONTRACT.md
Register your build in core/BUILD/REGISTRY.json
Never push. Never open PRs. Ember merges.
```

## Files
- **ALLOWED:** `core/BUILD/REGISTRY.json` (new) · `docs/codex/SESSION_CONTRACT.md` (new) ·
  `tools/merge/merge_gate.sh` (new) · `tools/merge/test_merge_gate.sh` (new) ·
  `docs/codex/HANDOFF.md` (add section only)
- **FORBIDDEN:** any service code · any existing spec · secrets · main branch

## Safety
- 🔴 Merge gate never auto-merges — it prints the command, Ember confirms
- 🔴 REGISTRY.json is Ember-owned — Codex writes `building/done`, only Ember writes `merged`
- 🔵 Kill-switch: if REGISTRY.json is missing, merge gate warns but does not block (graceful degradation)
- Rollback: `git revert` removes the gate script; REGISTRY.json deletable without side effects

## Tests
- `bash tools/merge/test_merge_gate.sh`
- Manually register a fake build, run gate, confirm PASS/FAIL logic

## Rollback
- `git revert <commit>` removes all new files
- Existing builds unaffected — REGISTRY.json is additive

## Close-out
- Update `docs/codex/HANDOFF.md` with build protocol section
- Proof: one build registered, gate run, merge confirmed
- Every future Codex session starts by reading `SESSION_CONTRACT.md`
