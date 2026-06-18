# d116 - Retroactive liveness audit d001-d092

Auto-seeded by d115 after the post-merge liveness probe mechanism exists.

## Build
Create a repo/server audit helper that checks whether merged decisions d001-d092 are actually live.

Scope:
- Read existing repo specs/results, merge history, activation scripts, ops_ledger rows, and safe local service/status evidence.
- Produce an audit report that classifies each merged decision as `live`, `not_live`, `unknown`, or `not_applicable`.
- Queue tightly scoped follow-up specs for `not_live` rows only.
- Do not deploy, push, merge, touch secrets, send outreach, stop/delete services, move money, or perform broad external scans.

## Context
- d115 closes the future merged-is-not-live gap with per-decision `liveness_check` probes.
- d116 closes the old gap by auditing d001-d092, which were merged before liveness probes existed.

## Proof expected
- A deterministic audit artifact lists d001-d092 liveness status.
- `not_live` rows are visible as follow-up build specs/decision rows.
- Audit execution is bounded, read-only by default, and logged to ops_ledger.

## Contract
Follow docs/codex/SESSION_CONTRACT.md. Branch off feat/headless-build (never main).
Register in core/BUILD/REGISTRY.json. Tests required. Do NOT push or merge.
