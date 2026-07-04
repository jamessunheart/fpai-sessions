# SPEC d154 — Campaign Watch: ads autonomy without credential exposure

**Intent (James 2026-07-04):** operate the live Meta campaign ("FP Assessment — Savings v1", campaign 52555196349772, act_71883338) autonomously. Harness correctly blocks sessions from reading raw credential stores — so the token stays server-side and sessions consume REPORTS.

## Build (on 162, where META_ACCESS_TOKEN already lives in a service env — reuse ad-portal/sparket-engine's env pattern; do NOT copy the token anywhere new)
1. `tools/ads/campaign_watch.py` + timer (2×/day): Graph API → campaign/adset/ad effective_status, review status, spend today/total, impressions, clicks, CPL (leads via pixel events), billing/funding status of act_71883338.
2. Writes `~/.config/fpai/ads/status.json` (mirrored into HOT_STATE scan + vault) and appends a row to the Allocation Ledger (this IS a Level-3 stewardship allocation being measured).
3. TG alert on state changes: review approved · first spend · CPL > $15 · daily spend > $12 (cap breach) · account/billing error.
4. Guarded ACTIONS endpoint (server-side, bearer-gated per AI-token convention): pause_campaign · resume_campaign · set_daily_budget (hard ceiling $20/day per feedback_cost_cap_20_per_day). Sessions call actions; never touch the token.

## Contract
$0 marginal · reversible (timer + files; kill = disable timer) · token NEVER leaves 162 service env · independent review before merge · register heartbeat + BURN_REGISTRY row.

## Done / Proof
status.json fresh (<12h) with real campaign numbers · one TG state-change alert observed · pause/resume round-trip tested once (campaign returned to prior state).
