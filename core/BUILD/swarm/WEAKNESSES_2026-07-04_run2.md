# Swarm run 2 (wecmilfc6) — 35 confirmed (15 high, 18 med)

- **[med] bug-guard / P8 compliance** — Two distinct defects, both confirmed live:

BUG-006 (curator collision): `debate.py` inserts REPO at `sys.path[0]` (lines 29-30), caching repo-local `
- **[high] observation-to-queue gap (RCA loop closure)** — Two confirmed sub-causes: (1) autonomous_rca.py run_rca() terminates by writing to ops_log + BUG_LOG.md only — zero calls to brain_index.decisions or
- **[med] resource-leak / reaper gap** — reap_worktrees.sh lines 122-126 gate removal exclusively on `is_merged_branch`. Any worktree whose build was BLOCKED, review-held, or hit a merge conf
- **[high] metric-validity / map≠territory (AI_PRINCIPLES coherence law** — verify_awareness.py:35-65 runs `ORDER BY weight DESC, ts DESC LIMIT 1` and returns the single highest-weight row. reliability_probe.py:108-129 records
- **[high] merged != live + proof channel structurally unwired** — Two compounding structural gaps confirmed against live code and DB state:

(1) `/opt/sh-brain-src/curator/decisions.py` line 412: `mark_merged()` exec
- **[high] repo != running (merged != live) on the primary user-facing ** — Two-directional fork: live bot was hand-patched (12 functions added directly to /opt/sh-brain-src/curator/tgbot.py, never committed), while the build
- **[med] metric_coherence / signal coverage gap** — SIGNALS list in /opt/fpai-build/FPAI_Cockpit/tools/governance/metric_coherence.py (line 28-41) contains exactly 1 entry: awareness_reliability. The di
- **[low] SSOT coherence / registry drift** — Two separate issues collapse into one claim, but only half is real. (1) AI_GOALS.md IS the real driver for session-level goal context — it was refresh
- **[high] repo≠running (map≠territory)** — The systemd unit (`fpai-build-loop.service`) runs `/opt/fpai-build/server_build_loop.sh` (189 lines, dated Jun 19), not the repo file at `tools/build_
- **[high] observation→build bridge missing: RCA emits findings to ops_** — The decision to NOT auto-queue was explicit and deliberate: `/etc/systemd/system/fpai-rca.service` line 8 reads "Does NOT auto-queue build fixes — fin
- **[high] metric-coherence / map-territory** — Two entirely separate instruments share the label "awareness reliability" but measure different things, with no reconciliation between them.

1. `reli
- **[med] signal routing — health failure → build queue gap** — health_check.sh writes `event=failed` to ops_ledger.jsonl and exits. Nothing reads that event class and converts it into a brain_index.decisions row.
- **[med] merged!=live (partial): one capture path works, one is dead** — Two independent bugs: (1) The explicit /correct Telegram command (tgbot.py lines 2900-2913) imports asyncpg which is NOT installed in the venv (Module
- **[high] merged≠live / designed-not-deployed gap in the learning pipe** — d141 (commit ec838f95, 2026-07-02) merged `tools/learn/sync_corrections_to_dataset.py` with no accompanying systemd timer or activation script. The re
- **[high] automated-learning-loop / API-auth-drift** — The service loads CLAUDE_CODE_OAUTH_TOKEN from /root/.config/fpai/claude.env via EnvironmentFile. The first two runs (Jul 03 16:15 and 18:15 UTC) succ
- **[high] metric-theater / learning-loop-integrity** — The "awareness reliability" metric measures only whether the latest session_insight title string appears in the bot's rendered BuildContext (verify_aw
- **[med] honesty / map-territory coherence** — NOW.md line 28 reads "engine self-runs (build · review · merge · learn)" but the entire ML training pipeline is unexecuted scaffolding: (1) FINETUNE_A
- **[med] state-drift / map-territory divergence** — Two independent failures compound: (1) NOW.md line 5 ("awareness 100%") and ALIGNMENT.md line 29 ("Awareness = 100%") are hand-typed during sessions a
- **[med] Observability / Alert-suppression** — Two compounding defects, both verified against live state:

1. **Rolling-average alert-gate silences single-probe failures when the 24h window is satu
- **[high] monitoring-gap / map!=territory** — Two compounding failures: (1) The deployed build loop at /opt/fpai-build/server_build_loop.sh is 189 lines and contains NO liveness probe code — d144
- **[med] honesty/P4-metric-theater** — The weakness is real but partially misfiled. Two distinct problems exist:

1. live_artifact_proof.py lines 128-139 (committed 2026-07-03, commit f0878
- **[med] map!=territory / metric drift** — Three concrete gaps confirmed in code: (1) LEARNING_METRICS.md line 28 self-admits LR is "partial — needs fixed benchmark suite." (2) No tool emits a
- **[high] guardrails** — The BACKLOG MERGE PASS loop (server_build_loop.sh lines 400-440) merges branches after only a curator import check (line 425). It never calls tools/me
- **[high] Watchdog boundary incomplete: hooks directory is protected b** — core/BUILD/PROTECTED_PATHS.txt lists `.claude/hooks/` but omits `.claude/settings.json` and `.claude/settings.local.json`. The prefix-match in ai_revi
- **[med] cost enforcement / autonomous loop safety** — The cap is measured but not enforced at any choke point that covers all paths. Three gaps compound: (1) cost-tally.sh line 195 always exits 0 — it is
- **[med] security / protected-path enforcement** — Line 49 of `/opt/fpai-build/FPAI_Cockpit/tools/merge/ai_review.py`:
`hits = [c for c in changed for p in prots if c == p or c.startswith(p)]`

When a
- **[med] Collision guard bypass — self-service override with no trust** — check-collision.sh trusts the filesystem alone: it reads SESSION_ID from stdin JSON (harness-provided but unverified), then checks whether .claude/ses
- **[med] governance** — The governance gate is wired to a dead entry point. `/etc/systemd/system/fpai-build-loop.service` ExecStart is exclusively `/opt/fpai-build/server_bui
- **[med] Allocation Intelligence / L6 Human Leverage** — Two hardcoded James-gates with no risk-tiered bypass:

1. `debate.py` line 447: `_ops("proposed", ..., "James: approve or veto the proposal")` — no co
- **[high] governance/enforcement** — ROUTE_RE is a closed 15-token literal-phrase enum. Training-bias deference is naturally paraphrased and hedged — 'happy to proceed if you confirm', 'w
- **[med] learning-loop completeness / prior drift** — JAMES_PROFILE_STUB (lines 23-27 of SERVICES/sunheart-brain/curator/decision_agent.py) is a module-level constant that is never written back. load_cont
- **[high] L4 (Bottleneck First) has no hard gate — advisory only; meta** — Three compounding failures: (1) constitution_check.py L4 entry (line 131) maps to "metabolism + Pragmatist lens" — neither emits exit 2, so no build i
- **[med] metric-coherence / boot-state drift** — MEMORY.md is injected into every Claude Code session as persisted context before any procedural steps execute. Its boot capsule (lines 1-31, `<!-- CAP
- **[med] memory-continuity / boot-sequence reliability** — MEMORY.md is 271 lines / 59,361 bytes and grows by appending new pins at the tail. Claude Code truncates the file at ~265 lines (~53.8KB) during conte
- **[low] signal-to-noise / boot coherence** — Two compounding issues verified against ground truth: (1) CLAUDE.md step 9 says "most recent file in sessions/" while DAILY_AWAKENING.md step 9 says "