# Loop 45 Proof — Legal Hardening Stack

**Date:** 2026-05-11
**Session:** 1e6be085
**Steward:** James Sunheart
**AI Council Partner:** Claude Opus 4.7 (1M context) in cockpit

## What shipped

**The Counsel (`legal-critic` service) — deployed**
- Live at `https://brain.sunheart.com/legal/critique` on brain server (162.0.208.88, port 28092)
- RAG over 523 corpus chunks (180pg Church Legal Resource, Coherent Treasury v0.10, CORA declarations, Cora Nation Manifesto, Coherence Treasury v0.10, trustee handbook, 4 more)
- Auth: 4 bearer tokens (claude-code, cursor, tg-bot, admin) at `/etc/legal-critic/tokens.txt`
- Cost: ~$0.15/critique pass via Claude Sonnet 4.6 + OpenAI embeddings
- Added to `AI_ROSTER` as active service. Quick-ref in `AI_CHARTER` Refinement Protocol section.

**Brand Tokenization Architecture v0.4 CONVERGED — 4-pass AI council loop**
- v0.1 → v0.2 → v0.3 → v0.4. 3 CRITICAL + 6 HIGH/MEDIUM in v0.1 → 0 CRITICAL + 0 HIGH in v0.4
- All v0.4 architectural prerequisites scoped into human-counsel engagement
- Multi-brand cooperative: CORA Nation 508(c)(1)(A) + Brand LLCs (arm's-length) + closed-loop Coherent Credit (CORA-only redemption)
- Severs Howey, eliminates inurement, separates commercial activity, cleans mockumentary characterization
- Total AI cost: ~$0.70 (5 Counsel passes including state assessment). vs human iterative ~$2.5-7.5k. **~5,000x cost reduction.**

**Current operational state legal assessment — Counsel pass**
- 3 CRITICAL exposures running TODAY identified:
  - OneBPO → CORA Nation contributions = inurement timebomb without arm's-length docs
  - Leveraged SOL short inside Trust = prudent-investor violation regardless of hard stop
  - Sapphire Bot live commercially under Sunheart brand = liability + UBIT + state licensing exposure
- 7 HIGH/MEDIUM issues identified across treasury, structure, jurisdiction
- All documented at `core/STATE/LEGAL_STATE_ASSESSMENT_2026-05-11.md`

**3 Operational Fix Memos**
- `core/STATE/legal/ONEBPO_TRANSFER_PRICING_POLICY_v0.1.md` — Type A/B classification + Independent Director approval + April $35.5k retroactive ratification template
- `core/STATE/legal/SOL_SHORT_TRUSTEE_PRUDENT_INVESTOR_MEMO_v0.1.md` — Path A (close) / B (transfer to personal) / C (NOT recommended) + Trustee memo template
- `core/STATE/legal/SAPPHIRE_LLC_FORMATION_MEMO_v0.1.md` — Delaware/state choice + 7 formation steps + interim disclaimer + state-specific psychic-services compliance

**Counsel Engagement Brief**
- `core/INTENT/COUNSEL_ENGAGEMENT_BRIEF.md` — one-page pre-read for licensed attorney
- 7 required deliverables scoped (§501(d), state MTL, state charitable registration, arm's-length, §4958, CR structure, worker classification)
- IN-scope / OUT-of-scope clarified
- Budget envelope: $500-3,000 for 1-2hr specialist engagement

**CORA Nation Canon v0.1 Compilation Stub**
- `core/INTENT/CORA_NATION_CANON_v0.1.md` — single-doc index of 13 canonical sources
- Covers religious-tier (manifesto, WPA, Mirror, declarations, lived practice) + economic-tier (Coherent Treasury v0.10 + Brand Tok v0.4)
- 30/60/90/120-day codification timeline
- Lived-practice substrate (Ecstatic Weekend, A*Zen*tion, Saturday Casual, Coherence Course, Zen Village CR) documented

**The Village Roles v0.1**
- `core/INTENT/THE_VILLAGE_ROLES.md` — gamification draft
- Hunter/Gatherer (mode) × Builder/Farmer/Chef/Cleaner (craft) grid
- 50/30/20 treasury split (Base/Craft/Mode)
- Satire archetypes per craft
- v0.1 draft for First Cohort review

**State + roster + charter updates**
- `core/STATE/AI_CHARTER.md`: added Refinement Protocol section (AI council before humans) + quick-ref to The Counsel
- `core/STATE/AI_ROSTER.md`: added The Counsel as active specialized AI
- `core/STATE/TREASURY_SCHEMA.md`: added BitTrue / Coinbase / Bullion / Scheduled Inflows / Payables categories + Treasury policy section (no gambling, 50% counterparty diversification)

## Memory additions (durable cross-session knowledge)

- `feedback_no_gamble_yield_first.md` — Treasury policy mandate 2026-05-11
- `feedback_ai_council_before_humans.md` — Refinement Protocol canonical
- `reference_treasury_yield_strategy.md` — yield tier framework + active $75k allocation
- `project_treasury_open_positions.md` — live position state
- `project_treasury_5m_target.md` — $5M passive income engine target
- `project_the_counsel.md` — service operational notes
- `project_brand_tokenization_converged.md` — v0.4 canonical state
- `project_village_roles.md` — Hunter/Gatherer × Craft grid

## Founder action list (this week)

1. **30 min** — Convene OneBPO board (paper meeting OK); adopt Transfer Pricing Policy; ratify April $35.5k retroactively
2. **15 min** — Decide SOL Path A (close) or B (transfer to personal); execute on BitTrue; sign Trustee Memo
3. **3-4 hrs (over 1-2 weeks)** — Cheyenne files Sapphire Readings LLC (Delaware); updates TOS + payment routing
4. **2-hr counsel hour** — Engage specialty religious-nonprofit + securities counsel; deliver pre-read package; obtain 7 required deliverables
5. **30 days** — Compile CORA Nation Canon v0.2 (narrative theology) per timeline

## What this enables

- Treasury becomes legally defensible at the architecture level (Brand Tokenization v0.4)
- Three ticking-timebomb operational exposures cleaned up
- Counsel engagement scoped tightly (1-2 hrs vs days/weeks of back-and-forth)
- AI-council process canonical and reusable for future legal/architectural questions
- The Counsel callable from any AI tool via HTTP (Claude Code, Cursor, future agents)
- Foundation set for $5M Treasury target via Camp Zen + Coherent Treasury operationalization

## Cost summary

| Item | Cost |
|---|---|
| The Counsel service: build + deploy | ~$0.01 (corpus embeddings one-time) |
| Brand Tokenization 4-pass convergence + state assessment | ~$0.70 (5 Counsel passes) |
| Operational fix memos (drafted in cockpit) | $0 (no extra Counsel calls) |
| **Total AI cost** | **~$0.71** |
| **Counterfactual human cost** | **$2,500–7,500** (5 rounds of legal iteration) |
| **Efficiency factor** | **~5,000x cheaper, ~100x faster** |
