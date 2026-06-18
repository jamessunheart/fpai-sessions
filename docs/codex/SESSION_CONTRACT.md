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

7. ACTIVATION SCRIPTS: if your build installs systemd units, modifies a live
   service, or requires any post-merge wiring step, ship an activation script at:
     core/BUILD/activate/SPEC_d{NNN}_{slug}.sh
   The build loop runs this automatically after merge. The script must be
   idempotent (safe to run twice), use `systemctl daemon-reload && systemctl
   enable --now <unit>` for timers, and patch any live service files if needed.
   Without activate.sh, the code lands but never starts — ship both or ship neither.

6. CROSS-PACKAGE IMPORTS: when importing from FPAI_Cockpit code into
   SERVICES/sunheart-brain/ code, NEVER use sys.path.insert() or sys.path.append().
   This causes curator package shadowing and breaks the live bot. Always use:
     import importlib.util as _ilu
     _spec = _ilu.spec_from_file_location("unique_name", Path("/opt/fpai-build/FPAI_Cockpit/path/to/module.py"))
     _mod = _ilu.module_from_spec(_spec)
     _spec.loader.exec_module(_mod)
     fn = _mod.function_name
   This pattern loads by explicit file path with no global path side-effects.
```

## Why this exists
Parallel Codex sessions on the same repo already produced a +619k-line near-miss PR to `main`. This contract + `core/BUILD/REGISTRY.json` + `tools/merge/merge_gate.sh` make parallel building safe: known branches, no rogue pushes, Ember-confirmed merges only.

## The merge gate
Before any merge, Ember runs `tools/merge/merge_gate.sh codex/<slug>`. It verifies the branch is registered `done`, tests pass, base is `feat/headless-build` (not main), and prints the merge command for Ember to confirm. It never auto-merges.
