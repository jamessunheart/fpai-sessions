# Session Handoff — Ember (Treasury + Patron Engine + Memory)
**Date:** 2026-06-12
**Session ID:** f98f2f16
**Branch:** feat/headless-build
**Register:** James-facing strategy + live ops (treasury deploys, fundraising architecture, memory infra)

---

## What this session built / changed

### Treasury — idle capital deployed to yield (James executed live)
- **Wise** ~$4.6k → interest enabled (~$207/yr)
- **Trust USDC** $6k → Kamino RockawayX RWA USDC vault, 6% (~$360/yr)
- **Trust SOL** $7.7k → JitoSOL staked (102.84 JitoSOL total, 5.45%, ~$495/yr)
- **MACU** ~$35k → money-market sweep DELEGATED to Richard (pending confirmation)
- **Venmo** $3.8k → left as operating buffer (no Savings feature on account)
- **BitTrue** ~$45k stables → deferred (KYC wall); **futures position CLOSED** (James confirmed — snapshot corrected)
- **New snapshot:** `~/.config/fpai/treasury/treasurer_resources_2026-06-12.md` (prior was 25 days stale)
- **Domain portfolio** added as asset class: ~$120-320k est (fullpotential.com ~60% of value). elifbetul.com intentionally lapsing.

### Fundraising architecture (NEW — strategy docs, not yet built)
- `core/STATE/PATRON_ENGINE.md` — the model: funnel bridging immediate income ↔ big-picture vision. Sell standing utility, gift the growing thing. Two doors: Membership (revenue) + Donation (508c1a, deductible).
- `core/STATE/CORA_NATION_FRONT_DOOR.md` — compliant page draft for cora-nation.com. Tier ladder (Citizen $44 → Patron $144 → Founding Patron $1,444 → Cora Circle $5-50k) + $250 Patron Gathering fast offer. Built from growth-architect tiers + compliance-scanner legal lines.

### Memory system (NEW — shipped, committed daa0148c)
- `tools/memory/build_memory_map.py` — Cartographer v0: complete map of 305 memories
- `.claude/hooks/memory-recall.sh` — UserPromptSubmit auto-recall, top-8 matches injected per prompt
- Triggered by failure: Camp Zen revenue plan sat invisible during strategy. Now structural.
- Kill: `EMBER_MEMORY_RECALL_DISABLE=1`

### Response format (aligns with sibling 0b0ca1df)
- Confirmed footer hooks disabled, NEXT+WHY only. Output style file already updated.

---

## Load-bearing facts surfaced this session
- 🔴 **Burn = $18.1k/mo (~$595/day).** Income ~$370/day (OneBPO $11k/mo + yield). **Currently ~$225/day NEGATIVE.** Runway 6.2mo (per sibling's financial dashboard seed).
- **OneBPO dropped to $11k/mo** (was modeled $15-30k) — corrected in snapshot.
- **Goal reframe from James:** daily income > daily expenses FIRST, then $1M liquid, then $5M.
- **Camp Zen Tier 1 = fastest non-James-time daily income** — village live (zenvillagecr.com), already burns ~$2.24k/mo empty. $500-600/wk/bed on record. 4 beds filled covers village burn in 1 week. Blocked only on James's pricing/capacity/date call.

---

## Open questions for integration session / James
1. 🟡 **Camp Zen Tier 1 pricing + bed count + first date** — the open daily-income move
2. 🟡 **PATRON_ENGINE legal gates** — state charitable-solicitation registration (unlocks Donation door) + Counsel on voucher/event language (unlocks Circle tiers). Membership door (Door A) needs NO legal clearance — can seed `/game/store` listings today.
3. 🟡 **MACU sweep** — Richard confirmation pending

## What NOT to rebuild
- Treasury deploys — done, live on-chain, snapshot written
- Memory recall system — shipped + tested + committed
- PATRON_ENGINE / FRONT_DOOR docs — drafted, awaiting James decisions not rebuild

## Suggestions
1. Membership door (Door A) can start earning with zero legal gate — seed the 4 tiers + $250 Gathering as `/game/store` listings
2. Camp Zen Tier 1 is the single fastest daily-income lever — needs only James's pricing call
3. Fold $18.1k/mo burn into all liquidity math — the $1M goal sits on top of a still-negative daily line
