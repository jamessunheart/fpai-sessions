# SPEC d094 — Wire The Forge as Pre-Build Scout

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What

Add a Forge scout step to `build_orchestrator.sh` that runs BEFORE codex builds each spec. The Forge reads the spec, searches for existing implementations and best practices, and appends findings to the spec so codex builds informed — not blind.

## Why

The Forge exists and has WebSearch + WebFetch but is manual-only. The build loop runs blind: it builds without knowing what already exists. We discovered Twilio, WhatsApp, Ollama, pgvector, n8n all existed only through manual audit — not because any agent caught them. A pre-build scout prevents reinventing the wheel on every spec.

## What the Forge checks for each spec

1. **Resource inventory** (`core/STATE/RESOURCE_INVENTORY.md`) — do we already have this tool/library/credential?
2. **Existing codebase** — does something similar exist in `/opt/fpai/` or `/opt/sh-brain-src/`?
3. **Web search** — what's the best practice / canonical library for this task? (2-3 targeted searches)
4. **PyPI / npm** — is there a maintained library that does 80% of this spec in 10 lines?

## Deliverables

### `tools/build_loop/forge_scout.sh`
```bash
#!/usr/bin/env bash
# Pre-build scout: runs The Forge against a spec before codex builds it.
# Appends a SCOUT REPORT section to the spec with findings.
# Output: SCOUT_FOUND_EXISTING=1 if something relevant exists (build may simplify)
#         SCOUT_BEST_PRACTICE=<library/approach> if canonical solution found
SPEC_FILE="$1"
claude -p "You are The Forge — pre-build scout. Read this spec and answer:
1. Does RESOURCE_INVENTORY.md already have a tool/library for this?
2. Is there existing code in the repo or /opt/fpai/ that covers this?
3. What is the canonical Python library or approach for this task?
4. What would you tell codex to use instead of building from scratch?
Be concrete. Under 200 words. Format: EXISTING: / LIBRARY: / BEST_PRACTICE: / SAVE:"  \
  --context "$(cat $SPEC_FILE)" \
  --context "$(cat core/STATE/RESOURCE_INVENTORY.md)" \
  >> "$SPEC_FILE"
```

### Integration into `build_orchestrator.sh`
- Add before the `run_codex.sh` call:
  ```bash
  bash tools/build_loop/forge_scout.sh "$SPEC_FILE"
  ```
- Scout output appended to spec → codex reads the full spec including scout findings
- Scout failures are non-blocking (log + continue — don't halt the build)

### `tools/build_loop/scout_log.jsonl`
- Each scout run logs: spec_id, timestamp, existing_found, library_found, estimated_time_saved
- Weekly summary surfaced to James via morning digest

## Gates
- Scout is non-blocking: if it fails or times out (30s), build proceeds without it
- Scout runs on `claude -p` ($0 marginal) — never metered API
- `FORGE_SCOUT_ENABLED=1` env flag (default on)
- `FORGE_SCOUT_DISABLE=1` to skip (emergency bypass)

## Proof
- Scout report appended to 3 specs before codex runs
- At least 1 spec simplified because scout found existing library
- scout_log.jsonl shows time/cost saved
