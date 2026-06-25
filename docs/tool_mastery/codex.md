# codex Mastery Card

## What it does best
Codex is best as a repo-native builder: read the existing code, make scoped edits, add tests, run verification, and report the exact files changed. It is strongest when the task is already routed into an approved build spec.

## Optimal use patterns (concrete, with examples)
- Give the target spec, allowed files, forbidden actions, branch/base rule, and proof expected. Example: "Build d046, register in REGISTRY, add tests, do not push or merge."
- Let Codex inspect before editing. The first useful move is reading repo context and call sites, not inventing architecture.
- Ask for implementation plus verification in one turn. Example: "Wire this into ai_review.py and debate.py, add tests, run focused unittest and py_compile."
- Keep blast radius narrow. Prefer small modules, existing helpers, and local tests over broad scans or unrelated refactors.
- Use Codex for repeatable repo work; route vault/live config/secrets/production steps to Ember or James.

## Anti-patterns (what silently degrades it)
- Asking for strategy, doctrine, treasury, people, or public-voice decisions without a routed downstream spec.
- Asking for huge unconstrained scans or edits across the whole service tree.
- Treating unverified code edits as complete without running tests.
- Letting Codex push, merge, deploy, delete, touch secrets, or modify production services.
- Giving ambiguous "improve the system" tasks without a concrete adjacent unlock.

## Effort/parameter settings for this system
Use Codex for buildstream tasks with workspace-write repo access. Prefer focused shell inspection with `rg`, `sed`, and targeted tests. Keep network and production effects disabled unless James explicitly routes that exact action.

## Key constraints and hard limits
Codex must follow `docs/codex/SESSION_CONTRACT.md`, register builds, avoid main, avoid pushes/PRs, and never perform Reserved Class actions. It must not revert user work or unrelated dirty files.

## How to detect it's not performing well
It stops at a proposal when the spec asked for a build, edits outside the requested surface, skips tests, broadens scope, ignores dirty worktree boundaries, or reports vague progress without files and proof.

## Last updated + source
Seeded 2026-06-16 from repo-local Codex contract, AGENTS orientation, and OpenAI/Codex usage patterns already mirrored in this workspace.

