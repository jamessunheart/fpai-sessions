# CODEX BUILD CONTRACT — read before writing any code

This is the guardrail that lets the recursive build loop run safely. Every Codex session follows it. Paste it at session start.

```
CODEX BUILD CONTRACT — read before writing any code.

1. BRANCH: always branch off feat/headless-build. Never branch off main.
   git checkout feat/headless-build && git pull && git checkout -b codex/<slug>

2. REGISTER: before writing code, add your build to core/BUILD/REGISTRY.json
   (status: "building"). Use a unique slug; two "building" entries with the
   same slug is forbidden.

3. BUILD: write code, run tests, commit locally. Do NOT push. Do NOT open PRs.

4. DONE: when tests pass, set your entry status: "done" in REGISTRY.json and
   commit that change. Tell James/Ember:
   "Done. Branch: codex/<slug>. Tests: N passed. Waiting for merge."

5. NEVER: push to main · open PRs to main · force-push · touch secrets ·
   auto-deploy. Ember handles all pushes, PR creation, and merges.
```

## Why this exists
Parallel Codex sessions on the same repo already produced a +619k-line near-miss PR to `main`. This contract + `core/BUILD/REGISTRY.json` + `tools/merge/merge_gate.sh` make parallel building safe: known branches, no rogue pushes, Ember-confirmed merges only.

## The merge gate
Before any merge, Ember runs `tools/merge/merge_gate.sh codex/<slug>`. It verifies the branch is registered `done`, tests pass, base is `feat/headless-build` (not main), and prints the merge command for Ember to confirm. It never auto-merges.
