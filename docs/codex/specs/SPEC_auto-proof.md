# SPEC_auto-proof

*Rung 1 of the self-standing ladder (Bar 4 — Auto-proof). See `docs/codex/AI_PROTOCOLS.md`.*
*Status: blessed by James 2026-06-06 (Cycle Zero). Executed live by Ember (small, contained, James present) rather than async Codex, to minimize James-touches in the first cycle.*

## Intent
Ships must leave evidence without a human hand-formatting it. Today proof is logged manually and dual-written (vault `00_MEMORY/PROOF LOG.md` + local `~/.claude/memory-global/PROOF_LOG.md`). Replace that friction with one command any builder calls at ship-time.

## Definition of Done
- A CLI `tools/proof/log.py` that:
  - takes `--summary`, `--unlocks`, and `--next` (required), `--stream` (default `Game`), `--actor` (default `AI(Ember)`), optional `--tested`, `--files`.
  - enforces the Buildstream Law: `--unlocks` must name the next adjacent intent, or honestly be `maintenance`, `decoration`, or `drift`.
  - rejects vague unlocks such as "improves the system" or "supports Heaven on Earth".
  - stamps `YYYY-MM-DD HH:MM TZ` in local time.
  - **prepends** a correctly-formatted row to the newest-on-top position of vault `00_MEMORY/PROOF LOG.md` (right after the `---` header separator).
  - mirrors the same row to local canonical `~/.claude/memory-global/PROOF_LOG.md`.
  - `--dry-run` prints the row + targets, writes nothing.
  - is secret-free, takes no money/network action, idempotent-safe (won't duplicate an identical row written in the same minute).
- Vault path resolves from `$FPAI_VAULT` or the default iCloud path (same pattern as `tools/decisions/daily_sync.py`).

## Files allowed
- `tools/proof/log.py` (new)
- `tools/proof/__init__.py` (new, empty)

## Files forbidden
- anything under `SERVICES/`, secrets, money tools, `.config`.

## Tests
- `python3 -m py_compile tools/proof/log.py`
- `python3 tools/proof/log.py --dry-run --summary "test" --unlocks "next adjacent test intent" --next "inspect dry run"` → prints, writes nothing
- vague unlock dry run exits nonzero
- live run → row appears at top of both proof logs, correctly formatted
- re-run same row same minute → no duplicate

## Rollback
- delete `tools/proof/`; both proof logs are append-only and entries can be hand-removed.
