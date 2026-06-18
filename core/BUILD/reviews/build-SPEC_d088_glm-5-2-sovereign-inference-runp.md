# AI Review — build/SPEC_d088_glm-5-2-sovereign-inference-runp

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds budget-guarded, kill-switched RunPod GLM scaffold + routes council Pragmatist through it with claude -p fallback; fails safe (no endpoint/key → fallback), no auto-deploy, no secrets hardcoded, no treasury/main touched — safe to merge with noted caveats.

## Findings
- Modifies the LIVE council loop (tools/council/debate.py, runs every 5min on server 162): all module-level logic was refactored into main(). Verified faithful — disabled-check, cost-cap, sig-hash dedup, diagnostic, blueprint, propose/dedup/gpt/recommend all preserved, and the file is executed as a script so main() still runs under cron. Tests cover the new helpers. Low residual risk but this is the highest-blast-radius change.
- Behavior change: pragmatist_voice() now triggers an EXTRA claude -p call (the fallback path) on every council run when no RunPod endpoint is configured — doubling claude invocations per debate. Flat-rate/$0 marginal so no metered cost, but adds latency. Not a guardrail bypass.
- Independent AI review was NOT completed by Codex (claude -p reportedly hung at ~90s and was terminated). This review is now the independent gate; that contract requirement is otherwise unmet — confirm acceptable.
- RunPod GraphQL schema (saveEndpoint mutation, spend query fields) is admittedly speculative/unverified — runpod_deploy.py is manual-invoke only and not wired into any loop, so a wrong schema fails the manual deploy rather than breaking the live system. Acceptable for a scaffold; verify on live host before activation.
- Fail-closed budget guard is correct: cutoff = 90% of cap (45 of 50), RUNPOD_BUDGET_DAILY_USD=0 and RUNPOD_GLM_DISABLE=1 both force claude -p fallback, missing key/spend-check failure → blocked. Good.
- Writes append rows to the live ops ledger /opt/fpai-build/ops_ledger.jsonl on server 162 (budget_alert + inference rows). Additive and matches the ledger's purpose; no destructive writes. No secrets are logged.
- No hardcoded credentials; RUNPOD_API_KEY/endpoint read from env only. Base branch is feat/headless-build (not main). Deploy creates GPU endpoints (real spend) but only via explicit manual run, budget-guarded.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
