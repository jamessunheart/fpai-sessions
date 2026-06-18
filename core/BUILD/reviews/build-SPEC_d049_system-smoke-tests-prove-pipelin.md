# AI Review — build/SPEC_d049_system-smoke-tests-prove-pipelin

**Verdict:** APPROVE · **Risk:** low

**Summary:** d049 adds 7-check live smoke suite, spec compliance checker, curator.decisions CLI, digest health rollup, and auto-records expected outputs after each auto-merge — all within spec scope, no money/identity/prod-server writes, kill switches present

## Findings
- build_orchestrator.sh now emits an autonomous `git add … && git commit` after every auto-merge to record diffs and expected_outputs.json — new behavior, within spec, but expands what the headless loop commits without James; low blast radius since `|| true` on failure
- recommend() passes build_spec as both build_spec and proof_expected fields — likely intentional default but semantically a copy-paste; no runtime harm
- Test 2 sends a real Telegram message every 6 hours (intended signal-check) — will add noise to James's chat; SMOKE_TEST_SILENT=1 suppresses it if needed
- health_check.sh MISSING case (no ops-ledger smoke row yet) only echoes WARN without calling fail() — fresh deploys skip the liveness gate for up to 6h, by design but worth knowing
- hardcoded fallback DSN `changeme@127.0.0.1:25432` appears in decisions.py and smoke_test.py — matches existing codebase pattern, env-var override present, not new exposure
- systemd units are repo artifacts only; result doc explicitly says do NOT install without Ember/James action — gate is clean

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
