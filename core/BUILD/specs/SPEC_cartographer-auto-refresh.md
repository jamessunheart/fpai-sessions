# SPEC_cartographer-auto-refresh

Keep the Cartographer's `SYSTEM_MAP.md` fresh automatically, so the auto-recall hook never serves a stale map. First build of the recursive-improvement loop — chosen because it is SAFE-AUTO (local repo only, reversible, no prod server, no money).

## Problem
`tools/memory/build_system_map.py` produces `SYSTEM_MAP.md` (the ~1,200-resource map the recall hook `.claude/hooks/memory-recall.sh` reads). It is rebuilt only when older than 24h, or manually. A memory/state file added today is not discoverable via recall until the next rebuild — the exact "memory sat invisible" failure the Cartographer was built to end.

## Build
1. **`tools/memory/refresh_system_map.sh`** — a thin wrapper that runs `python3 tools/memory/build_system_map.py`, debounced: skip if the map was rebuilt within the last 5 minutes (timestamp file `~/.config/fpai/cartographer_last_refresh`). Print the resource count on rebuild, "skipped (debounce)" otherwise.
2. **`.claude/hooks/cartographer-refresh.sh`** — a PostToolUse hook that calls `refresh_system_map.sh` in the background (non-blocking) when an `Edit`/`Write`/`MultiEdit` touches a memory, `core/STATE`, or `core/BUILD` file. Reads the hook JSON from stdin; exits 0 always.
3. Wire the hook into `.claude/settings.json` PostToolUse chain (append after `log-edit.sh`). Match `Edit|Write|MultiEdit`.

## Done / Proof
- `bash tools/memory/refresh_system_map.sh` rebuilds the map and prints the resource count.
- A second run within 5 minutes prints "skipped (debounce)" and does not rebuild.
- Editing a memory/state file triggers a rebuild within one tool call (SYSTEM_MAP.md mtime updates).

## Files
- **ALLOWED:** `tools/memory/refresh_system_map.sh` (new) · `.claude/hooks/cartographer-refresh.sh` (new) · `.claude/settings.json` (append one PostToolUse hook entry) · `tools/memory/test_refresh.sh` (new)
- **FORBIDDEN:** changes to `build_system_map.py` logic · any prod server (162/198/209) · secrets · the `main` branch · any `SERVICES/` code

## Tests
- **`tools/memory/test_refresh.sh`** — (1) running refresh produces a non-empty `SYSTEM_MAP.md`; (2) an immediate second run is skipped by the debounce. Print "RESULT: N passed, M failed" and exit non-zero on any failure.

## Safety / Rollback
- Reversible: `git revert` removes the new files; the hook is additive and degrades gracefully (background, exits 0).
- The map rebuild is read-only over the filesystem; it only writes `SYSTEM_MAP.md`.
