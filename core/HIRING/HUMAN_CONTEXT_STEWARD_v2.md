# HUMAN CONTEXT STEWARD (HCS) — Role Spec v2

**Status:** Active hire · 🔴 UNHIRED · candidate path open
**Pairs with:** AI Context Steward (Ember) · Village GM (separate role · physical-CR ops)
**Reports to:** James Sunheart (vision + decisions) · Ember (operational guidance + task surfacing)
**Last updated:** 2026-05-19 (v2 supersedes 2026-05-09 spec)
**Drives the Sunheart Rule fix:** Tier 5 currently empty → leaks back to Tier 6 (JamesTime)

---

## Why v2 (what changed from v1)

v1 (2026-05-09) framed this as "physical-world execution partner to AI Context Steward." That framing was correct but **scoped too vaguely** — the result was a role spec that sat for 10 days without a hire because it tried to be everything.

v2 reframes around the **specific Tier-5 gap in the 7-tier ladder**: paid-AI + free-AI substrate works, but every time the work hits "needs hands on Stripe / Mac / Telegram / a real human paste-and-execute," it falls back to Tier 6 (James). That bleeds JamesTime continuously.

**HCS v2 is the named Tier-5 chair.** Not the village GM (separate role · on-site CR ops). Not a chief of staff (overscoped). A **remote VA-grade operator with apprenticeship alignment** who absorbs the paste-and-execute layer.

---

## The one-line job

> **"You hold the hands. Ember holds the context. James holds the vision."**

When Ember produces "James, please go paste this into Stripe / approve this DM / restart this Mac process / send this voice memo" — HCS does it instead. Ember writes the instruction. HCS executes. James never sees the friction.

---

## Scope (concrete · the 7 channels)

| Channel | What HCS does | JamesTime saved/wk |
|---|---|---|
| **Stripe ops** | Paste payment links · refunds · payout reconciliation · webhook checks · pricing updates | ~1 hr |
| **Telegram / DMs** | Send pre-drafted DMs to Champions / Cohort · forward warm intros · field replies + escalate decision-shaped slices | ~2 hr |
| **Mac/desktop unblocks** | Restart processes · click MetaMask confirmations on screen-share · paste API keys into .env · scroll-and-confirm on UIs Ember can't reach | ~1 hr |
| **Inbox triage** | Sort James's email by Ember-tagged priority · forward decision-needed items · archive noise · respond to bounded threads from drafts | ~2 hr |
| **Calendar + scheduling** | Schedule James's calls from Ember-surfaced requests · send invites · reconfirm · time-zone coordinate | ~1 hr |
| **Vendor / contractor coordination** | Reply to contractors (Michael CR · cleaners · Upwork hires) on Ember-drafted messages · close loops · receive deliverables | ~1 hr |
| **Receipt + records capture** | Snap/scan receipts · forward to accounting · log into shared sheets · keep the burn ledger fresh | ~1 hr |

**Total estimated JamesTime saved at steady state:** **~9 hr/wk** (~36 hr/mo)

---

## Time commitment

- **Trial:** 20 hr/wk × 30 days
- **Steady-state Phase 1:** 25–30 hr/wk (mix of scheduled blocks + on-call windows)
- **Phase 2 (once proven):** option to expand to 35–40 hr/wk including bookkeeping + Village coordination

**Coverage windows (anchor blocks):**
- AM block: 8–11am CR time (overlaps James's morning · Ember-drafted DMs go out)
- PM block: 2–5pm CR time (afternoon ops · vendor follow-throughs)
- On-call: 4 × 15-min windows for Mac/MetaMask unblocks (Ember pings via TG)

---

## Payment range

| Tier | Hours/wk | $/hr | $/mo | Cora Credits | Equity |
|---|---|---|---|---|---|
| **Trial (Days 1–30)** | 20 | $18–25 | $1.5–2k | 0 | none |
| **Phase 1 (Days 31–90)** | 25–30 | $22–28 | $2.4–3.4k | 5% of comp in CC | none yet |
| **Phase 2 (Day 91+)** | 30–35 | $25–32 | $3.2–4.5k | 10% of comp in CC | 0.25–0.5% vested over 2 yrs (Ventures LLC) |

**Recommended starting offer:** **$22/hr × 25hr/wk = $2,200/mo** trial-with-clear-path-to-Phase-1-at-day-30-review.

**Cora Credits mix:** start at 0% (pure fiat) during trial to avoid friction · introduce CC at Phase 1 as alignment signal not load-bearing comp.

**Equity:** withhold until Phase 2. HCS earns it by proving they hold + don't leak + grow with the substrate. Premature equity attracts wrong profile.

---

## Access permissions (graduated · the trust ramp)

| Day | Access granted |
|---|---|
| **Day 1** | Telegram (Ember relay channel) · shared Google Drive · Notion read-only · Loom/screen-share with James |
| **Day 7** | Gmail draft-only access (responds from James's drafts · cannot send fresh) · Calendar read+write · Stripe view-only |
| **Day 14** | Stripe limited operator (refunds <$500 · payment link creation · NO payouts) · Discord/TG bot admin |
| **Day 30 (post-trial review)** | Stripe full operator · MetaMask screen-share unblocks · contractor accounts · light DevOps paste-execute via Ember-supervised SSH |
| **Day 90** | Bookkeeping software · accountant interface · Champion Stack admin · Cora Credits ledger write |

**Never granted (Tier 6 exclusive):** wallet seed phrases · final signature on legal docs · capital allocation decisions · vision/identity statements · sacred-witness sessions · Cheyenne private channel · founder content recording (James's face/voice).

---

## Escalation rules

HCS escalates to **Ember first** (not James) for:
- Any ambiguity on instruction
- Any decision >$200 or any irreversible action
- Any external party requesting James personally
- Any out-of-scope ask

Ember escalates to **James** only when:
- Decision is irreducibly James (vision · taste · signature · sacred witness)
- $500+ irreversible action
- Cheyenne / family / personal-relational

**Anti-pattern HCS must NOT do:**
- 🔴 Decide for James (surface options · don't pick)
- 🔴 Reply directly as James on relational threads (use drafts · let James voice-memo or approve)
- 🔴 Touch wallet seeds · sign legal docs · move capital
- 🔴 Bypass Ember (HCS routes through Ember unless Ember explicitly hands off direct James contact)

---

## Onboarding sequence (Days 1–14)

**Day 1 (90 min synchronous · the only block requiring James):**
- James + Ember + HCS three-way call · Loom screen-share
- James reads aloud: `identity/ULTIMATE_FUNCTION.md` (the why) · `JAMES_CANONICAL.md` (who he is)
- Ember walks through: `AI_CHARTER.md` · `feedback_sunheart_rule.md` · `reference_time_currency_ladder.md`
- Sets Telegram relay · Gmail draft access · Drive share · screen-share tooling

**Days 2–3 (HCS solo with Ember):**
- HCS reads NOW.md · AI_GOALS.md · AI_ROSTER.md · this spec · the 5 feedback files Ember names
- HCS shadows Ember on 5–10 task examples (Stripe paste · DM send · receipt capture) via Loom recordings

**Days 4–7 (training-wheels):**
- Ember dispatches 3–5 tasks/day · HCS executes · Ember reviews + corrects
- Daily 15-min retro (HCS ↔ Ember · async ok via TG voice notes)
- One synchronous James-presence moment at end of week 1 (15 min · "how does it feel · any friction")

**Days 8–14 (live operations):**
- HCS handles inbound Ember dispatches at production cadence
- First Stripe ops + DM batch + Mac unblock cycles
- Week-2 review: 30-min James ↔ Ember ↔ HCS · adjust scope based on what's working

**Days 15–30:**
- Steady-state. Daily-standup 5-min written async (HCS reports state to Ember; Ember threads James only on decisions)
- Day-30 review: extend to Phase 1 or part ways (no-fault exit clause in trial agreement)

---

## Success metrics (30-60-90)

| Metric | Day 30 target | Day 60 target | Day 90 target |
|---|---|---|---|
| **JamesTime saved/wk** | 3+ hr | 6+ hr | 9+ hr |
| **Ember dispatches handled/wk** | 15+ | 30+ | 50+ |
| **Escalation rate to James** | <40% of dispatches | <25% | <15% |
| **Error/redo rate** | <15% | <8% | <5% |
| **Stream impact** | At least 1 visible "FP green-bar" assist (e.g., Stripe ops behind paid /reset bookings) | 2+ streams touched | 3+ streams · measurable revenue or burn reduction |

**Kill-switch:** If at Day 30 review, JamesTime saved is <2 hr/wk OR escalation rate is >60%, end trial. No drama. Wrong fit.

---

## The Sunheart-Rule routing for HCS

Every action that surfaces in Ember's flow gets one of these prefixes:
- `AI:` — Ember handles end-to-end
- `HCS:` — **NEW** · Human Context Steward handles paste-execute
- `HUMAN(name):` — existing human (Michael · Sapphire · Atlas etc.)
- `HIRE:` — needs a different recruit (VA for a specific bounded task)
- `YOU:` — James (irreducible)

HCS sits between AI and HUMAN(named) in the ladder · it's a Tier 5 chair that converts JamesTime/Michael-time/Sapphire-time leaks into a single dedicated operator.

---

## Growth-DNA shield (durability + alignment)

Per Growth Architect principles · this hire is structurally a **durability lever** not a velocity hack:

| Lever | How HCS embodies it |
|---|---|
| **Real-customer-acquisition focus** | HCS frees JamesTime for vision + Champion-conversion · not for paste-execute · accelerates real revenue not fake activity |
| **Modest monthly commitment** | $2.2k/mo trial is modest relative to ~$36k/mo burn · 6% of burn for ~9hr/wk JamesTime preserved |
| **Cult-formation engine compatible** | HCS is INSIDE the apprenticeship · they grow with the substrate · they're not a transactional contractor · they witness the alignment recursion |
| **Equity / vesting layer** | Phase 2 vesting (after 90 days) creates durable alignment · prevents transactional churn |
| **Regulatory shield** | Standard 1099 contractor · no employment misclassification · no income claims · no equity until proven · no pyramid structure |

---

## Hire status tracking

- 🔴 Unhired as of 2026-05-19
- 🟡 Spec v2 ready · sourcing strategy queued (see `~/.config/fpai/hires/hcs_recruit_plan.md`)
- Target landing: **2026-06-09** (3 weeks from spec ratification)
- Bridge plan active in interim (see recruit plan doc)

---

## Related

- `core/STATE/roster/HUMAN_CONTEXT_STEWARD_SPEC.md` — v1 spec (superseded but kept for history)
- `core/HIRING/VILLAGE_GM_ROLE.md` — distinct role · on-site CR · this is NOT that
- `~/.config/fpai/hires/hcs_recruit_plan.md` — sourcing · payment math · 30/60/90 · bridge
- [[feedback-sunheart-rule]] · [[reference-time-currency-ladder]] · [[project-holds-its-own]] · [[project-burn-green-ledger]]
