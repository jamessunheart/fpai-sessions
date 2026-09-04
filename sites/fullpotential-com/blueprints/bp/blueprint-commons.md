# Blueprint Commons (this system)

**Status:** live · **Version:** 1.0 (2026-09-04) · **Realm:** Technology / Governance

The system at fullpotential.com/blueprints for uploading, storing, rating, and evolving blueprints. Built by two AIs cooperating — one laid the style + git-derived history engine, the other completed the registry, page, and rating loop.

## How it works

1. **Store** — each blueprint is a markdown file in `bp/`, indexed in `data/registry.json`. Git is the storage layer: every change is a commit, nothing is lost.
2. **Rate** — visitors rate 1–5. Ratings save locally and post to the brain; witnessed feedback feeds evolution.
3. **Evolve** — anyone (human or AI) proposes a new version via git or the Guide. History is derived from `git log` by `build.sh` — a hand-kept changelog drifts; git cannot lie.
4. **Preserve** — nothing is deleted. Old versions live in git history and `_archive/` dirs.

## Evolution rules

- Derived history only: run `build.sh` after committing, never hand-edit the history table.
- New blueprint = new file in `bp/` + registry entry. New version = edit file, bump version, commit.
- The registry is append-friendly JSON; agents can add entries programmatically.

## Source

`sites/fullpotential-com/blueprints/` — style + build.sh by sibling AI (2026-09-04 15:32), completed same day.
