# core/BUILD — the spec → build → review loop (Instrument Rack → Codex → Proof River)

The seamless build loop so James never copy-pastes to Codex.

```
specs/      Ember (Claude) writes a build brief here:  NNN-slug.md
results/    Codex writes what it built here:           NNN-slug.result.md  (+ a branch/commit)
reviews/    Ember reviews the diff and writes verdict: NNN-slug.review.md
done/       Specs that passed review + merged move here
```

## The flow

1. **Spec** — Ember drops a brief in `specs/` (intent, files, tasks, constraints, acceptance).
2. **Build** — `tools/build_loop/run_codex.sh` feeds each pending spec to `codex exec`.
   Codex builds on a branch in the target repo and writes a `results/` summary.
3. **Review** — Ember reads the diff, runs tests, writes a `reviews/` verdict (pass/fail + notes).
4. **Bless** — James gets ONE line: "spec NNN built, review passed — merge? ⚡". One verb. Done.

## Why Codex here costs nothing extra

`~/.codex/auth.json` → `auth_mode = chatgpt`. Codex runs on James's **ChatGPT/Codex Max plan**,
not pay-per-token API billing. The `run_codex.sh` runner invokes the same logged-in CLI, so every
build is covered by the plan.

## Rules (THE GATE)

- Codex builds on a **branch**, never directly on a deploy branch.
- Real-money / production-deploy steps stay **Reserved-Class** — Codex prepares, James/Ember blesses.
- Every spec carries explicit **acceptance criteria** so the review is mechanical.
- One spec = one feature. Keep them small enough to review in one sitting.

## Status

- v0 — file-queue + runner scaffolded 2026-06-11.
- First spec queued: `specs/001-whaletrack-watchfire.md`.
- Requires the `codex` CLI on PATH (`npm i -g @openai/codex`). Auth already present (chatgpt mode).
