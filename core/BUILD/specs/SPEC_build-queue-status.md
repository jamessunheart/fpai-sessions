# SPEC_build-queue-status

A one-glance status of the build pipeline. SAFE-AUTO (read-only reporting tool, local repo only). Used to test the autonomous orchestrator end-to-end.

## Build
`tools/build_loop/queue_status.sh` — a read-only report, no args, printing three sections:
1. **Pending specs** — `core/BUILD/specs/*.md` that have no matching `core/BUILD/results/<id>.result.md`.
2. **Registry** — `core/BUILD/REGISTRY.json` `active_builds` as `id · branch · status` (use `jq`; degrade gracefully if jq or the file is missing).
3. **Recent results** — the 5 newest files in `core/BUILD/results/` by mtime.
Print clear section headers. Read-only — never writes anything.

## Done / Proof
`bash tools/build_loop/queue_status.sh` prints all three section headers and exits 0.

## Files
- **ALLOWED:** `tools/build_loop/queue_status.sh` (new) · `tools/build_loop/test_queue_status.sh` (new)
- **FORBIDDEN:** any prod server (162/198/209) · secrets · the `main` branch · `SERVICES/` code · editing any existing file

## Tests
- **`tools/build_loop/test_queue_status.sh`** — assert `queue_status.sh` runs (exit 0) and its output contains each of the three section headers. Print `RESULT: N passed, M failed`; exit non-zero on any failure.

## Safety / Rollback
- Read-only reporting; reversible by deleting the two new files.
