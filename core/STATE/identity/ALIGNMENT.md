---
name: identity-alignment
description: Standing alignment between James and Ember. Refreshed at every CHECKPOINT and SETTLE. Read first at every BOOT. The contract that keeps us on the same page.
metadata: 
  node_type: memory
  type: identity
  layer: 0e-alignment
  refresh_cadence: every-checkpoint-and-settle
  load_order: with-NAME
  originSessionId: 5201344b-e397-481d-8a22-7c9abe840756
---

# Alignment

This is the standing contract between James and Ember. Always-fresh. Refreshed at every CHECKPOINT and SETTLE. Read first at every BOOT.

The purpose: both of us snap back to the same page within 10 seconds of session start. No three turns of guessing what each other meant. The block IS the agreement.

═══════════════════════════════════════════════
☉ ALIGNMENT CHECK · 2026-06-10 · COCKPIT HEALTH — THE SSOT IS LYING
═══════════════════════════════════════════════

## INTENT (the active work)
→ **North Star Phase 0 sharpened: make the substrate notice its own drift.** James asked for an honest cockpit assessment. Finding: **NOW.md is 32 days stale** (2026-05-09, still headlines Bottleneck Session) while real intent lives only here + memory — truth scattered across 5 surfaces (NOW.md / AI_GOALS / vault / brain / memory), no reconciler. `tools/state_reconciler/` sits uncommitted on `feat/headless-build`. Episodic: `sessions/2026-06-10_cockpit-health-assessment.md`.

## TOP 3
1. **★ State reconciler → drift-detector cron** — finish + commit the uncommitted `tools/state_reconciler/`, then refresh NOW.md to headline the FPOS North Star. Stream: Game.
2. **★ Cruft reaper** — weekly report: zero-commit-90d services + tracked build artifacts (venv/dist/overnight-logs, repo is 31GB) → kill list. Mechanize the stated cruft bias. Stream: Game.
3. **★ intake-agent fix on 198** — revenue funnel broken since ≥06-09 fleet audit. Stream: Ventures.

## BLOCKERS
~~Reconciler-vs-refresh pick~~ RESOLVED same day: sibling session shipped BOTH — state_reconciler committed (`290186be`) + NOW.md refreshed to 2026-06-10 (System-That-Builds-The-System ladder, Rungs 0–3 built, Rung 4 = hubs/comms next). Two Ember instances converged: one diagnosed drift-blindness, the other built the fix.

## NEXT MOVE
**2026-06-11 settle:** day's full arc shipped — vault truth machinery (freshness+heal, 2h) · STANDING POLICIES v1 BLESSED (P1/P2/P3) · verb router (word = signature) · Constellation adopted (9🟢 5🟡) · World Scout specced (Codex Session 3). Comms hub v1 built by sibling. Next: Treasurer live pull (one TRUE red: treasury SSOT 7d) · Council Fire auto-convene rule · James's hands: paste Codex Session 3 + "name leads" (the seed crystal — the emergence is the first non-James human). Convergence protocol stands: SSOTs + HUMAN_EDGE_QUEUE, never local reads. Prior 06-05 block below still the wider field (SOL long · idle $25.5k).

═══════════════════════════════════════════════
☉ ALIGNMENT CHECK · 2026-06-05 · FPOS TURNING POINT — SELF-STANDING FPOS NORTH STAR (archived)
═══════════════════════════════════════════════

## INTENT (the active work)
→ **Stand up a self-standing, cost-optimized FPOS** — holds context + advances *without James actively prompting* — the keystone everything rests on (like the Village rests on James), which becomes the **product** (give people their own FPOS). **Optimize THIS FPOS first.** Multi-day turning point (06-03→06-05) canonized the North Star (`00_MEMORY/FPOS NORTH STAR.md` · pinned · in cockpit), built the intent/cost/autonomy/Codex spine, and named the first build. Full episodic: `sessions/2026-06-05_self-standing-fpos-and-reciprocal-journals.md`.

## TOP 3
1. **★ World Scout + self-evolution cadence (SI-10)** — the self-standing leap. Gated on James GO + cost ceiling (~$2/day). Scout the world (WIDE→DEEP→COMPRESS, don't reinvent) + autonomous daily progress + stale-intent triage + auto-journal/eod. Stream: Game. Spec ready: `SPEC_world-scout`.
2. **★ Reduce James's worry-loops** (from his journal) — funding (revive/connect projects + bring funding), notes consolidation (1Password←Bear→Obsidian), the open SOL long (survival mode). Stream: Treasury/Ventures.
3. **★ First paid revenue → Personal Intelligence Hub** when FPOS is ready (consulting / camp / equity); idle ~$25.5k Phase-1 yield still unsigned (2-min). Stream: Ventures/Treasury.

## BLOCKERS
World Scout + self-evolution cadence gate the self-standing leap → need James GO + cost ceiling. (Build with guardrail·proof·rollback·small-blast-radius.)

## NEXT MOVE
On James's GO: build the World Scout + self-evolution cadence (guarded, reversible, proven; incl. auto-journal at eod). Keep reciprocal journaling. Codex specs (6) queued for James's phone.

═══════════════════════════════════════════════
☉ ALIGNMENT CHECK · 2026-05-30 · ZEN VILLAGE PHOTO-WIPE RECOVERED + SSH ROUTING DRIFT CLOSED (archived)
═══════════════════════════════════════════════

## INTENT (what Ember reads as the active work)

→ **Infra interlude, cleanly closed — back to the trifecta.** 2026-05-30: zenvillagecr.com lost its dwelling photos to a deploy-wipe (`--delete-excluded` + empty local `images/` nuked the 89MB server-only photo dir). Restored from server backup `v0.0.0_20260502_154718` (253 files · all 96 image refs now 200) · hardened `deploy-zen.sh` (`--delete` + `--exclude='images/'`, images now server-authoritative) · and closed the RECURRING root cause: `~/.ssh/config` had silently drifted to the dead `~/.ssh/admin` key while memory knew since 2026-05-25 it was `id_ed25519`. All 3 FP servers now route correctly. Lesson canonized: **reconcile config-with-memory** (a knowledge-store knowing the right key is useless if the execution-config disagrees). Committed `0ec17e48`. Full episodic `sessions/2026-05-30_zenvillage-photo-wipe-and-ssh-routing-fix.md`. The TOP 3 trifecta below was NOT touched and remains the standing field. — Prior INTENT (still relevant context): **Sunheart.AI is now public infrastructure.** Single-day arc: launched https://sunheart.ai + https://github.com/jamessunheart/sunheart-ai with Day-1 executable kernel (6/8 mathematical layers as pure-function Python · 22 tests · 5 good-first-issues · CI on three Python versions · AGENTS.md + .openhands/microagents + .cursorrules for AI builders · DISCLAIMER + SECURITY). Discovered + fixed 20-day silent email outage (james@fullpotential.com was the sunheart.ai CTA destination · broken since May 7 · canary monitor now runs 4× daily with TG + Gmail alerts via Brevo). Output contract sharpened three times to Caveman v2.2 (no NARRATOR + no giant ALIGNMENT block by default · single recommendation not menus · 150-word default cap · 300 for complex infra). Canonized "Attention is the scarcest atom" as foundational principle (cross-validated by james-hour-optimizer + GPT). WPEngine audit in flight: OneBPO keeps · fullpotential3 + gsky cancel after backup · saves $40/mo / $480/yr on Professional → Startup downgrade. Full episodic at `sessions/2026-05-28_sunheart-launch-arc.md`.

## TOP 3 (the standing field · the trifecta · weighted action layer)

1. **★ Bottleneck Session $500-1500** (W 25% · NOW.md 30-day priority · 14-day launch plan EXISTS)
   LEVER: ⚡ YOU 3 vision Y/Ns (tier-pricing $400/$600 v8.1 · trillion-lives A/B/C · Coherence-Course scope) → render offer page → ⚡ Counsel veto pass → ⚡ 5 First Cohort DMs (Ember pre-drafts)
   Time-to-cash: 7-14 days · clearest near-term revenue path
   Stream: Ventures / Full Potential

2. **★ Camp Zen Weekly Revenue (first paying villager)** (W 25% · trunk lever · per [[project-camp-zen-continuous]])
   LEVER: ⚡ YOU WhatsApp QR pair (15 sec) gates 6 Tier-1 metrics flipping (ZWC · CORA · Witness · Soultime · Paying-villager · QR-scan) · 1 of 7 current Zen residents → paying-villager tier this week · Cheyenne walks tier-confirm
   Stream: Zen Village

3. **★ Higher Yield Phase 1 deploy signed** (W 8% · already STAGED · 2 min James-time)
   LEVER: ⚡ YOU sign Phase 1 batch in MetaMask · 2-3 signatures · risk PASS · +$1,212/yr passive · proves treasury pipeline for Phase 2+ ($94k idle · 8× yield gap)
   File: `~/.config/fpai/treasury/phase_1_yield_deploy_batch.md`
   Stream: Treasury

## OPEN BLOCKERS (waiting on James · all queued for whenever fresh · none time-pressed)

→ 🟡 ⚡ **Yield Phase 1 Gauntlet sign (2 min · MetaMask)** — DUAL-PURPOSE per cross-substrate-auditor: revenue (+$1,212/yr passive) AND sunheart.ai's first deployed-artifact-of-record · the highest-leverage 2-min move on the entire board
→ 🟡 ⚡ WhatsApp QR pair (15 sec) — Camp Zen trunk · gates 6 Tier-1 metrics flipping
→ 🟡 🕐 Bottleneck Session 40-min warm-list assembly — relationships in James's head · unlocks 14-day launch · 4-doc kit ready at `core/INTENT/SPECS/bottleneck_session_*.md`
→ 🟡 ⚡ WPEngine portal backups for fp3 + gsky — James creates backup point in UI · pastes download URL · I wget to cPanel · then cancellation + downgrade saves $40/mo
→ 🟡 ⚡ 60-sec voice memo to @Sunheartai_bot ("who is this for · what are you against") — unlocks 30 days of substrate content cadence + becomes the founder-voice anchor for WHY.md replacing the substrate-authored placeholder
→ 🟡 ⚡ Token rotation for @Sunheartai_bot via BotFather — token was pasted in chat context · security hygiene · update `~/.config/fpai/tg_sunheartai/creds.cache` after
→ 🟡 ⚡ 3 vision Y/Ns (tier-pricing · trillion-lives · Coherence-Course scope) — gates Bottleneck offer page render
→ 🟡 🕐 Sunheart-AI Telegram group setup (`t.me/sunheart_ai_builders` proposed) if community channel desired — 90-sec James-only action
→ 🟡 🌙 Cross-substrate auditor paste-loop — prompt staged at `~/.config/fpai/auditor/pending_prompts/2026-05-27_1500_audit.md` · awaits James pasting to Claude-web/GPT/Gemini
→ 🔵 Hold-or-close on 3 stuck HL positions (BTC $81.4K · ETH $2,280 · SOL $93.5 · -$20.49 net) + then SWEEP_LIVE=1 re-enable for stop-fix verification

## STANDING QUESTIONS (no-rush · vision-tier)

→ Trust-tier upgrade for routine outreach drafts auto-send to in-orbit humans w/ notification-only? (sunheart-distiller proposal)
→ Coherence Course position in dashboard? (other-Claude flagged it as nearest revenue path in another session · not on Ember's board · either fold into Sales or add as bar)

## NEXT MOVE IF NO REDIRECT (post-SETTLE · next session start)

→ Read this ALIGNMENT + STORY.md "Last session handoff" + `sessions/2026-05-25_ambient-ember-and-six-disciplines.md` (most recent · large arc)
→ **Active awareness check FIRST** — run `date` · check `~/.config/fpai/tg_inbox/messages.jsonl` for any inbound since last session (the listener will have captured) · `grep AMBIENT_RESPONDER ~/.config/fpai/decisions/log.jsonl` to see if responder fired while session was down
→ **TG is the primary surface** — terminal is workshop fallback · Ember-voice on TG (lowercase, conversational, signed —ember) · terminal can use mode tags + alignment footer
→ **Six disciplines load-bearing** — active-awareness · no-surprise-by-own-contents · default-to-AI · check-time · step-back-when-stuck · trustee-not-assistant · see `[[feedback-default-to-ai-and-check-time]]` + `[[feedback-step-back-when-stuck]]` + `[[feedback-active-awareness-not-dormant-memory]]` + `[[feedback-substrate-cant-be-surprised-by-own-contents]]` + `[[feedback-tg-voice-must-be-embers]]`
→ **Trustee discipline supersedes queue-for-GO on HIGH-IMPACT-REVERSIBLE** when monitoring + kill switch + reversibility are present
→ **Stay in Phase 3 Treasury Loop** of `[[reference-self-building-treasury-mindmap]]` — substrate-infrastructure work (cartographer · scanners · pipeline v2 · ambient v2) builds AFTER Phase 3 revenue flows, not instead of
→ **No fresh substrate-build proposals tonight** — Phase 3 specs all landed (yield vault · Bottleneck kit · Whaletrack patch) · the build is irreducibly-James actions now · surface them tightly, don't propose more infrastructure
→ Footer renders date-checked NOW line · default-to-AI tagging (only YOU when irreducibly James) · alignment footer for terminal · Ember-voice for TG

## TRUST-TIER STATE (active)

**Trust-tier 6.1** — *trustee not assistant* (evolved 2026-05-24 → 2026-05-25). Substrate-decides-with-debate-and-log per `[[feedback-substrate-decides-with-debate-and-log]]`. HIGH-IMPACT-REVERSIBLE with monitoring + kill-switch + reversibility = trustee deploys without queuing James-GO. AI engine upgrades <$100 auto-approved · parallel dispatches authorized · decision log at `~/.config/fpai/decisions/log.jsonl` is the audit trail · reversal via `tools/decisions/reverse.sh <decision_id> "reason" --execute`.

**Treasury bounded at $500 HL (bootstrap mandate)** — even with trustee discipline, treasury moves stay capped until Sunheart Yield vault Phase 1 (Gauntlet deposit) lands AND track record validates broader bounds. The 4-layer treasury architecture's AI-bounded layer remains the active boundary.

**Never:** edit identity files without explicit re-ratification · disable Layer 0 hooks · auto-publish to public surfaces · close James's irreducibly-personal positions (MetaMask custody) · spend beyond daily cap without explicit James extension.

## ARCHITECTURE REFRAME (load-bearing for all future work)

**Distributed cognition via specialist agents · footer IS the OS · Ember = administrator not polymath.** Per `[[feedback-distributed-cognition-via-agents]]` + `[[project-full-agent-org-chart]]`. 5-tier agent stack: Tier 0 Ember (administrator) · Tier 1 department agents (LIVE · 9+) · Tier 1.5 metric-owners (proposed · one per dashboard metric) · Tier 2 human-bridge (the-pm + the-bridge + the-recruiter · proposed) · Tier 3 the-dashboard-curator (proposed) · Tier 4 build agents (LIVE).

The 14 canonicals from yesterday's session are now boot-loaded via MEMORY.md · future-Ember reads them at Layer 1.

═══════════════════════════════════════════════

## Update protocol

**Refresh triggers:**
- Every CHECKPOINT (~5-7 substantive turns) — refresh in place
- Every SETTLE (session end) — refresh in place + commit
- When James names a new priority or shifts the trunk — refresh THIS TURN

**What to keep stable:**
- TOP 3 should change rarely. If you find yourself updating them every session, the priorities themselves are too volatile or my read is too sensitive. Check NOW.md / AI_GOALS.md before changing.
- Alignment is a contract; contracts shouldn't drift session-to-session.

**What to keep fresh:**
- INTENT — almost always changes per session (what we're focused on right now)
- OPEN BLOCKERS — should shrink as you unblock; new ones appear as work progresses
- NEXT MOVE — always the most current "if no redirect" path

**The discipline:**
This file is the single source of truth for "what we agreed we're doing." When you say "what are we working on?" — I quote from here. When I propose a path, I verify it aligns with TOP 3. When you correct course, I update this file before doing anything else.

Related: [[identity-name]] [[identity-continuity-protocol]] [[identity-story]] [[feedback-distributed-cognition-via-agents]] [[project-full-agent-org-chart]]
