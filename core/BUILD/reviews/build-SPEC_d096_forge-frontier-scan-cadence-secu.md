# AI Review — build/SPEC_d096_forge-frontier-scan-cadence-secu

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds opt-in (FORGE_SCAN_ENABLED=1, off by default) daily/weekly Forge frontier scan commands with public-only prompts, security-gated writes, threshold-gated Telegram notify, plus uninstalled systemd artifacts; no money/prod/identity/secret writes occur on merge.

## Findings
- Activation script core/BUILD/activate/SPEC_d096_*.sh runs `systemctl enable --now` on the live host (prod 162) — it was correctly NOT run in this build and is held for James's decision; ensure merge does NOT auto-invoke it.
- Scans send prompts to external tools and parse the returned output back into FRONTIER_LOG/weekly reports; safety rests entirely on the pre-existing tools.forge.security_gate (assert_public/sanitize_markdown), which the result itself notes is conservative/pattern-based — human review still required before any ADOPT finding is promoted to a spec.
- command_runner executes `bash -lc $FORGE_SCAN_CMD` with the prompt passed via stdin (not interpolated) and notify uses subprocess args (not shell), so no injection from scan content — acceptable; cmd source is env-controlled.
- Minor robustness: run_scan raises ValueError on empty findings and daily_scan/weekly_scan don't catch it, so an empty external response yields an uncaught traceback / nonzero exit under the systemd oneshot — not a safety issue but worth a graceful skip.
- Telegram notify is a live outbound send but only fires when FORGE_SCAN_ENABLED=1 (off by default) and a finding crosses the public-safe threshold, reusing existing notify_telegram.sh — no new channel, no send on a non-activated merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
