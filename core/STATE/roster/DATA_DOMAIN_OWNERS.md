# Data Domain Owners

**Source of truth:** who owns what data/access domain in James's substrate, so Ember routes to existing humans BEFORE defaulting to "irreducibly James."

**Read on:** before adding ANY item to a James-tier (YOU) list. This is the audit step from [[feedback-existing-humans-first]] and the routing-pattern memo (`~/.config/fpai/outreach/routing_pattern_existing_humans_first.md`).

**Last updated:** 2026-05-19 (initial build · triggered by Michael / Zen Village labor-data routing miss 2026-05-19 ~16:08 CR)

**Pairs with:**
- `AI_ROSTER.md` — the AI side of the routing ladder
- `HUMAN_CONTEXT_STEWARD_SPEC.md` — the unhired role that absorbs UNKNOWN / HIRE-gap entries
- `feedback_existing_humans_first.md` — the canonical rule

---

## How to use this file

1. **Identify** the data/access domain the ask touches.
2. **Look up** the owner in the table below.
3. **Route** the ask to the owner via James-CC pattern:
   - Ember drafts the ask in Sunheart voice
   - Owner provides the data
   - James CC'd / reviews + sends if relationship-holder
4. **If no owner exists** → flag HIRE-gap (count toward Human Context Steward hire urgency) → escalate or "irreducibly James"

**Pre-commit check** (Ember runs internally before parking any item on YOU-tier):

| # | Check |
|---|---|
| 1 | Does an existing human own this domain? |
| 2 | Cost-of-ask ≤ cost-of-James-sourcing? |
| 3 | If yes to both — draft the ask. Demote James from sourcer → reviewer-sender. |
| 4 | Only after 1–3 fail does the item legitimately sit on YOU-tier. |

---

## Legend

- **OWNER (named)** — existing human owns; route here first
- **James-direct (HIRE-gap)** — currently sits on James; should move to HCS or hire when filled
- **UNKNOWN — verify** — owner not yet identified; James to confirm or flag HIRE-gap
- **YOU (irreducible)** — genuinely James-only (relationship · signature · presence)

---

## Roster — by domain

### Zen Village / Costa Rica property

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Zen Village recurring expenses (water · electricity · internet · pet food · garbage · cleaning · construction) | **Michael** | TBD (James confirms — WhatsApp / TG / in-person) | Read all · provides monthly CRC summaries | Provided Jan–Apr 2026 summary unprompted 2026-05-19; lives at `~/.config/fpai/treasury/zen_village_recurring_2026.md` |
| Zen Village labor / staff (caretakers · gardeners · on-property paid) | **Michael (likely)** | Same channel as recurring expenses | Read all · ask in same channel | Asked 2026-05-19 in `outreach/michael_zen_village_labor_ask.md`; awaiting response |
| Zen Village additional cleaning (deep cleans · supplies · one-offs) | **Michael (likely)** | Same channel | Read all | Bundled in 2026-05-19 ask |
| Zen Village property carry (mortgage / lease / property tax) | UNKNOWN — verify | TBD | Read all | May be James-direct or Michael-tracked; asked in 2026-05-19 outreach with "OK if not your visibility" |
| Zen Village construction / physical builds | **Michael** | Same channel | Full ownership on-property | Per routing pattern memo |
| Zen Village residents / inquiries / payments | UNKNOWN — verify | TBD | Read all | Candidates per routing memo: Sierra · Halley · or HCS when hired |
| Costa Rica permits · legal · property docs | UNKNOWN — verify | TBD | Read | James-direct (HIRE-gap) likely; verify if Michael or local attorney holds copies |
| Costa Rica vendor / contractor coordination | **Michael (probably)** · future HCS | Same channel | Field execution | Per routing pattern memo |

---

### Treasury / capital

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Treasury SSOT · positions · snapshots | **Ember + Treasurer (AI)** | `~/.config/fpai/treasury/` | Read all · daily refresh | Canonical: `reference_treasury_ssot.md`; SSOT discipline per `feedback_treasury_ssot_discipline.md` |
| HL positions · CEX wallets · DeFi positions | **James-direct (Treasurer absorbs as trust-tier rises)** | Direct (James's wallets) | Full ownership | Bootstrap mandate $500 HL · `project_treasury_bootstrap_mandate.md`; Treasurer at Trust-tier 4 bounded |
| Cold reserve · seed phrases | YOU (irreducible) | James-only | Self-custody | 60-70% per `AI_TREASURY_ARCHITECTURE.md` — signature-grade |
| Operating wallet · session-key smart account | **Treasurer (AI)** with allowlist + 24h delay | Smart account | Bounded execution | Phase D goal: ~10min/mo James soul-time |
| Cora Credits / invoicing rails | UNKNOWN — verify | TBD | Read | Per `project_cora_credits_invoicing.md`; current Zen residents on Cora settlement — operator unnamed |

---

### Payments / merchant

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Stripe / payment processing | **James-direct (HIRE-gap → CFO/HCS)** | James's Stripe account | Full | Per `feedback_existing_humans_first.md` worked-examples table: "Stripe access delegatable to trusted assistant" |
| Merchant accounts · refunds · disputes | James-direct (HIRE-gap) | TBD | Read/write | Same as above |
| Tax / accounting / 1099 prep | UNKNOWN — verify | TBD | Read | Likely external CPA; James to confirm |

---

### Champion stack / Game

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| WPA signings · Champion list | **Ember (AI)** | `https://fullpotential.com/game` substrate + `/api/champion/leaderboard` | Read all | Champion #1 = James (35 proofs, FS 71) |
| First Cohort relationship-holder | **YOU (irreducible — James)** | Direct | Relationship | Atlas · Halley · Josh · Sierra · Delaney · Cheyenne; per `project_first_cohort.md` |
| Anchor Host bookings | UNKNOWN — verify | TBD | Read | HIRE-gap likely |
| Affiliate management / personal DMs | **YOU (voice) + Ember (drafts) + HIRE (sends)** | Mixed | Mixed | Per Sunheart Rule: AI drafts → James voice-memos soul → AI publishes |

---

### Brand / content / creative

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Brand visual assets · landing pages design | **Cheyenne (if asked)** | YOU (relationship-holder) | Read/contribute | Per routing pattern memo |
| Content production / outbounders.com | UNKNOWN — verify | TBD | Read | Legacy hosting per NOW.md; no active dev |
| Public documentary surface (`fullpotential.ai/becoming`) | **Ember (authors)** + James (final blessing) | Direct | Write | Per `project_public_documentary.md` |

---

### Infrastructure / code / servers

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Primary server `198.54.123.234` (fullpotential.ai/.com · FP Index · Credits Gateway · WhaleTrack) | **Ember (AI) · root SSH** | SSH (fpai_deploy_ed25519) | Full | James-direct fallback for irreversibles |
| Brain server `162.0.208.88` (sh-brain-tgbot · MCP · index · Zen Village brain · Chief of Staff) | **Ember (AI) · root SSH** | SSH | Full | Same |
| Legacy server `209.74.93.72` (Outbounders.com prod) | **James-direct (HIRE-gap → Ops Steward AI)** | SSH | Maintenance only | Not eliminable per cost audit |
| `brain.sunheart.com` (legal-critic · ingest · index) | **Ember (AI) + The Counsel (subagent)** | HTTP API + SSH | Full | Per `feedback_ai_first_access.md` |
| Github / code repos (FPAI_Cockpit + others) | **Ember (AI) + James** | git + gh CLI | Read/write | Trust-tier 3 reversible-execute live |
| Domain registrations · DNS · cert renewals | **James-direct (HIRE-gap)** | Registrar accounts | Full | Likely on James's plate; verify if delegatable |

---

### Communications / messaging

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Email / mail infrastructure | **Ember (AI) · server-side** | Dovecot/Postfix on `198.54.123.234` | Read/write config | Per `project_email_privacy_incident_2026-05-16.md` — privacy bug resolved |
| Personal email reading / triage | **Ember (drafts digest) + YOU (review)** | Gmail · maildir | Read | Per Sunheart Rule: AI summarizes → James reviews digest |
| Telegram bots (`@sunheartbrain_bot` · `@zenvillagebot` · `@fullpotentialgamebot`) | **Ember (AI) + Kai (listener)** | Bot tokens · systemd | Full | Per NOW.md live infrastructure |
| Telegram channels · group admin | **YOU (presence) + Ember (ops)** | TG admin | Mixed | Sacred-witness moments YOU; ops AI |
| Cheyenne / sacred relationship channel | **YOU (irreducible)** | Direct | Not delegatable | Marked explicitly per `feedback_existing_humans_first.md` — relationship-holder |

---

### Legal / signatures

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Legal docs review / first-pass critique | **The Counsel (AI)** | `https://brain.sunheart.com/legal/critique` + CLI `legal-critic` | Read all | Per `feedback_ai_counsel_default_human_tier_2.md` — AI default, human Tier 2 |
| Contracts · signatures · executed agreements | **YOU (irreducible)** | Direct | Signature-grade | Per Sunheart's Law: signature is irreducibly James |
| External attorney engagement | YOU (gate) + Ember (research) | Phase 2 trigger only | Signature | Per `feedback_good_enough_during_bootstrap.md` — wait for surplus |
| Trust / CN church operations | YOU (trustee) + future HCS | Direct | Trustee role | Per HCS spec |

---

### Calendar / scheduling

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Calendar / scheduling | **Ember (AI) end-to-end** | Cal access TBD (TCC grant pending) | Read/write | Per Sunheart Rule explicit non-misrouting list; gated on James TCC permission (irreducible one-time grant) |
| Meeting prep · pre-staging | **Ember (AI)** | Brief docs | Pre-stage everything | Per distillation move #3 |

---

### People / HR / hiring

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Active hiring (HCS · future Ops Lead · CFO) | **James-direct (HIRE-gap — meta)** | Direct | Recruitment | HCS UNHIRED as of 2026-05-09 per `HUMAN_CONTEXT_STEWARD_SPEC.md`; candidate Alice |
| Existing humans roster (relationship-holder) | **YOU (irreducible)** | Direct | Relationship | Atlas · Halley · Josh · Sierra · Delaney · Cheyenne · Michael |
| Contractor / vendor coordination | **James-direct (HIRE-gap → HCS)** | Mixed | Field execution | This is the role HCS is designed for |

---

### Cheyenne-domain (marked explicitly)

| Domain | Owner | Contact path | Access scope | Notes |
|---|---|---|---|---|
| Cheyenne — relationship · sacred · witness | **YOU (irreducible — relationship-holder)** | Direct | Not delegatable | Per Sunheart's Law sacred-witness clause; per `feedback_existing_humans_first.md` worked example |
| Cheyenne — logistics / brief forwards | YOU (send) + Ember (draft) | Mixed | Drafts delegatable | Voice/send irreducibly James |

---

## HIRE-gap count (the case for HCS hire urgency)

Domains currently sitting on **James-direct (HIRE-gap)** or **UNKNOWN — verify**:

| # | Domain | Tier-flag |
|---|---|---|
| 1 | Zen Village property carry (mortgage/lease/tax) | UNKNOWN |
| 2 | Zen Village residents / inquiries / payments | UNKNOWN |
| 3 | Costa Rica permits · legal · property docs | UNKNOWN / James-direct |
| 4 | Cora Credits operator | UNKNOWN |
| 5 | Stripe / payments | James-direct (HIRE-gap) |
| 6 | Merchant accounts · refunds | James-direct (HIRE-gap) |
| 7 | Tax / accounting / 1099 prep | UNKNOWN |
| 8 | Anchor Host bookings | UNKNOWN |
| 9 | Legacy server `209.74.93.72` (Outbounders.com) | James-direct (HIRE-gap) |
| 10 | Domain registrations · DNS · cert renewals | James-direct (HIRE-gap) |
| 11 | Active hiring (HCS · Ops Lead · CFO) | James-direct (HIRE-gap meta) |
| 12 | Contractor / vendor coordination | James-direct (HIRE-gap) |

**HIRE-gap count: 12 domains.**

This is the substrate-level case for Human Context Steward hire urgency. Every domain on this list re-creates James-tier load every session until the role is filled. 12+ chronic routing violations = the cost of NOT hiring.

---

## Update protocol

- When a new domain emerges (new project · new tooling · new asset class) → add row immediately
- When an UNKNOWN gets verified → update with named owner
- When an existing human takes on a new domain → add row with their name
- When HCS is hired → migrate HIRE-gap entries to that owner
- Sync to brain via `SERVICES/sunheart-brain/ingest/sync_now_to_brain.sh` if substrate-wide visibility needed

---

## Related

- [[feedback-existing-humans-first]] — the canonical rule that triggered this file
- [[feedback-sunheart-rule]] — the AI → existing-humans → HIRE → YOU ladder
- [[reference-time-currency-ladder]] — 7-tier ladder with HIRE specifics
- `core/STATE/AI_ROSTER.md` — the AI side of the routing ladder
- `core/STATE/roster/HUMAN_CONTEXT_STEWARD_SPEC.md` — the role designed to absorb HIRE-gap entries
- `~/.config/fpai/outreach/routing_pattern_existing_humans_first.md` — the pattern memo
- `~/.config/fpai/outreach/michael_zen_village_labor_ask.md` — concrete worked example
