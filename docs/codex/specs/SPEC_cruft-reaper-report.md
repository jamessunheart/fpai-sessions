# SPEC_cruft-reaper-report

*For Conscious Codex 2 (hygiene domain — new `tools/reaper/`). A READ-ONLY weekly reaper report: surface frozen services (zero commits 90d but still running), tracked build artifacts (venv/dist/logs/overnight-logs), and oversized paths → a kill-list of candidates. Turns the long-stated "bias toward deleting" into a system. Owner: Codex. Report only — NEVER deletes or stops anything.*

## Source / why
Fable 5 audit (2026-06-10): repo ~31GB with `venv/`, `dist/`, `overnight-logs/` tracked, 261 mostly-paused services, and "bias toward deleting" stated since May but never automated. Matches memory `feedback-cruft-bias`. Make the vibe a report.

## The three declarations
- **Milestone (DoD):** `tools/reaper/scan.py` writes `docs/codex/REAPER_REPORT.md` — a ranked kill-list: each candidate with path/service · reason (zero-commit-90d · tracked-artifact · size) · evidence · suggested action (untrack / stop / archive) · a 🔴 "James approves any deletion" banner.
- **Dependency:** none. Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main`.

## Definition of Done
1. Scan: services with no commit in 90d but a running/enabled systemd unit · tracked build-artifact paths (venv/dist/__pycache__/logs) · paths over a size threshold.
2. Rank by (cost/size × staleness). Output the report ONLY — every row is a *candidate*, not an action.
3. A `.gitignore` *suggestion* block for the tracked artifacts (printed, not applied).
4. Tests: a fixture repo → report lists the planted stale service + tracked artifact; nothing is deleted/stopped/modified; dry-run == normal run (read-only).

- Files ALLOWED: `tools/reaper/**` (new) · `docs/codex/REAPER_REPORT.md` (new) · read-only everywhere else. FORBIDDEN: deleting/stopping/untracking anything · editing services/systemd · `git rm` · money/send/deploy/secrets.

## Safety
- 🔴 Report only. It NEVER deletes, stops a service, untracks a file, or edits .gitignore. Each cleanup is a separate James-approved act.
- Rollback: delete `tools/reaper/` + the report.

## Close-out
HANDOFF 📥 · PROOF LOG (cruft bias is now a weekly report, not a vibe) · BRICK. James triages the kill-list when ready.
