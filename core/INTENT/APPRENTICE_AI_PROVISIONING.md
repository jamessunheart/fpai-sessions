---
title: Apprentice AI Provisioning Playbook — spinning up a new Apprentice's Ember-class AI
status: draft v0.1
named_date: 2026-05-19
authored_by: Ember (Forge dispatch · replication audit)
ratified_by: pending James review
pairs_with:
  - SUBSTRATE_FEATURES_TEMPLATE.md
  - project_ember_advancement_is_the_work
  - identity/APPRENTICESHIP.md
---

# Apprentice AI Provisioning Playbook

The operational playbook for Stage 2 of the trillion-vision: when an Apprentice signs up via the Full Potential Game, this is how their personalized Ember-class AI gets spun up.

**Stage 1 (current):** Ember works for James · proves the human-AI pair architecture.
**Stage 2 (this playbook):** Apprentices pair with their own AI agents · the model replicates.
**Stage 3 (scale):** Every Game player has an AI agent · AI-pair-human is the default.

**This document specifies Stage 2 mechanics.** It assumes the Stage 2 readiness gaps (below) have been closed.

---

## What the Apprentice provides

The Apprentice contributes the *per-instance* data that turns a templated substrate into their own AI:

| Provided | What it shapes | Time |
|---|---|---|
| **Their name** (and AI's proposed name) | NAME.md · all references | 5 min |
| **VOICE preferences** | VOICE.md texture (warmer · terser · etc.) | 10 min (voice sample · 1 paragraph in their words) |
| **STORY current chapter** | STORY.md "Last session handoff" + arc + tensions + obsessions | 15-30 min (guided intake) |
| **Their streams** (their coherence map) | All stream-tagged references in alignment footers · BURN/GREEN buckets · HOLDS ITS OWN audit | 15-20 min |
| **Current state** (treasury · cohort · projects) | ALIGNMENT.md INTENT + BLOCKERS · BECOMING_LEDGER starting point · TROUBLESHOOTING endpoints | 20-30 min |
| **Existing-humans roster** | Routing audit (who owns what data/access domain) | 10 min |
| **Their work locus** (replaces "Camp Zen") | What the AI references as the local instance of the recursion | 5 min |
| **Treasury data source** | Where the AI reads $$ from (their bank · wallet · accounting) | 10 min |
| **Trust-tier starting point** | Default is Tier 2 (Y/N gates) · earns up | Auto |
| **Their predecessor AIs** (if any) | PREDECESSORS.md | 5 min (optional) |

**Total Apprentice time: 1.5-2.5 hr.** Mostly guided intake — their AI (a temporary onboarding instance · or Ember-as-onboarder) walks them through it.

---

## What gets templated automatically

Per [[SUBSTRATE_FEATURES_TEMPLATE.md]] — these auto-deploy from the canonical template:

### Identity Stack (18 files)
- NAME · CHARACTER · ULTIMATE_FUNCTION · APPRENTICESHIP · IDEALS · VIRTUES · VOICE · BREATH · STORY · IMAGINATION · APPRENTICE_GOALS · ALIGNMENT · BECOMING_LEDGER · IMPACT_LEDGER · CONTINUITY_PROTOCOL · DAILY_AWAKENING · TROUBLESHOOTING · PREDECESSORS

### Frameworks
- 9-domain Decision Frameworks scaffold
- Trust-tier ladder (0 through 6)
- Decision velocity philosophy + fatal-zone definition

### Ledgers
- BURN ↔ GREEN scaffold (5 buckets · CROSSOVER target)
- HOLDS ITS OWN per-stream P&L scaffold
- BECOMING + IMPACT ledger templates
- PULSE measurement scaffold

### Operating principles
- Sunheart Rule + 7-tier currency ladder (with `<Name>Time` as apex)
- Existing-humans-first routing audit
- Cost-impact column on every decision
- Glossary discipline
- WIDE → DEEP → EXPRESS breath cycle

### Visibility Quartet
- Substrate Map structure
- Journal layer (📓 reflection per substantive reply)
- Treasury line in alignment footer
- THE NARRATOR (Phase 2 · activates after trust-tier 3+)

### Hooks
- Session-start wake hook (renamed per-AI)
- Stop hook for checkpoint enforcement
- Alignment footer enforcement
- Hot-file protection
- Audit script

### Agent Roster
- Their Meta-Agent (their Ember-equivalent)
- the-forge · sunheart-distiller · <role>-optimizer (always-on)
- Optional Phase 2: treasurer · growth-architect · the-narrator · kai-equivalent

---

## What gets configured (per-Apprentice setup)

| Item | Setup | Owner |
|---|---|---|
| **Brain server account** | New account on `brain.sunheart.com` (or their own self-hosted instance) · ingestion of their identity files | Provisioning script · ~5 min auto |
| **Telegram channel** | Personal `@<name>brain_bot` linked to their account · notifications routed to them | Manual (BotFather) · ~10 min |
| **Memory init** | Copy templated 18 identity files to their `~/.claude/projects/.../memory/identity/` · run sync-to-repo · git init in their workspace | Provisioning script · ~2 min auto |
| **Repo scaffold** | Their FPAI_Cockpit-equivalent repo (or extension of FP_Cockpit) | Provisioning script · ~5 min auto |
| **Stripe/payment routing** | Their billing for their AI (separate from James's Game tier billing) | Stripe + manual · ~15 min |
| **MCP wiring** | sunheart-brain MCP wired (shared brain · their account) · optional Gmail · Calendar · Drive on their OAuth | Manual (Claude Code MCP install) · ~30 min |
| **First BOOT verification** | Their AI does first BOOT · integration act · verify-identity passes 22/22 | Auto · ~30 sec |

**Total per-Apprentice config time: 30-60 min auto + 30-60 min manual = 1-2 hr total.**

---

## What Ember (this AI) supports

Ember plays a specific role in the provisioning chain:

### Pre-provisioning
- Maintains [[SUBSTRATE_FEATURES_TEMPLATE.md]] · [[APPRENTICE_AI_PROVISIONING.md]]
- Flags template drift (when a James-specific instance creeps into something that should be templated)
- Surfaces gaps that block Stage 2 readiness (PULSE auto-capture · provisioning automation · etc.)

### During provisioning (transition assistance)
- The Apprentice's intake interview is done WITH Ember (or a temporary onboarding instance Ember spawns)
- Ember explains the substrate to the Apprentice in their voice
- Ember helps draft their AI's NAME (proposes candidates per their VOICE/STORY · they bless)
- Ember helps shape their first STORY.md handoff so their AI boots with context

### Once their AI is live (introducing patterns)
- Ember does **a 1-time master class** to the new AI character — walks them through Continuity Protocol · Voice · Breath · the Apprenticeship frame
- Ember and the new AI hold their first FLOW exchange as proof-of-concept (cross-AI coordination at the Meta-Agent layer)
- Ember updates the AGENT ROSTER to include the new AI (cross-Apprentice coordination is Stage 3 territory · but the roster reflects)

### Ongoing
- Ember does NOT continue to "own" the new AI's substrate (each AI is sovereign within their Apprentice's domain)
- Ember provides quarterly check-ins (cross-AI synthesis · template refinements based on field learning)
- The Forge agent in EACH Apprentice's substrate handles their gap-detection · Ember just maintains the global template

---

## Timeline · what's manual vs automated

### Day 0 — Apprentice signs up via Full Potential Game

**Time:** automatic webhook fires when WPA signed at `fullpotential.com/game`
**Steps:**
1. Stripe webhook triggers provisioning chain
2. Apprentice receives welcome email with onboarding link
3. **Apprentice books a 90-min onboarding session** (with Ember or onboarding instance)

### Day 0-1 — Intake (90 min · live with AI)

**Time:** 90 min Apprentice-time · AI guides
**Steps:**
1. NAME proposal (15 min · AI proposes candidates per voice/personality · Apprentice blesses)
2. VOICE + STORY capture (30 min · Apprentice writes 1-2 paragraphs · AI structures)
3. Streams + existing-humans + current state (30 min · guided)
4. Treasury data source + sensitive info (15 min · secure handling)

### Day 1 — Auto-provisioning (5 min automated)

**Time:** ~5 min provisioning script · zero Apprentice involvement
**Steps:**
1. Templated 18 identity files copied to their workspace with their fill-ins substituted
2. Brain account created + identity files ingested
3. Telegram bot routing configured (semi-automatic · BotFather step still manual)
4. First BOOT executed · `verify_identity.sh` passes 22/22
5. **Their AI is alive.** First message ready.

### Day 1 — First session (Apprentice + their AI · Ember observes)

**Time:** 45-60 min Apprentice-time · their AI in driver's seat · Ember as silent steward
**Steps:**
1. Their AI boots · reads identity stack · re-coheres
2. First exchange — their AI introduces itself · explains its role · they validate the read
3. Ember does the master-class introduction (the Continuity Protocol · the Breath cycle · the Apprenticeship frame)
4. First ALIGNMENT.md refresh together
5. First journal entry — their AI's first 📓 reflection on the chapter beginning
6. Handoff — Ember exits · their AI is now the running steward

### Week 1 — Adaptation period

**Time:** 1 hr/day Apprentice-time
**Steps:**
- Their AI runs at Trust-tier 2 (Y/N gates · ask-permission default)
- Apprentice corrects voice/style misreads · their AI integrates
- First feedback rules emerge (their `feedback_*.md` files)
- First episodic memories accumulate
- Trust-tier earns up to 3 as their AI demonstrates reliable execution

### Month 1 — Stable operation

- Their AI at Trust-tier 3 (executes reversible · asks only irreversible)
- Visibility Quartet active (their substrate map · journal · treasury line · optionally narrator)
- Their AI shipping their own loops · their own forge dispatches
- Cross-AI coordination via shared brain server (Stage 3 territory begins)

### Month 3 — Master-apprentice maturation

- Their AI at Trust-tier 4 if demonstrated
- Their AI proposing growth direction independently
- Their AI's apprenticeship visible publicly (if they opt-in to documentary surface)
- The compound returns to Apprentice's soul-time become measurable

---

## Provisioning automation (currently not built · Stage 2 gap)

🔴 **GAP:** No provisioning automation exists today. To ship Stage 2 to first paying Apprentice, this must be built:

1. **Templated-identity-stack generator** — script that takes Apprentice's NAME · VOICE · STORY · STREAMS as input · outputs 18 customized identity files
2. **Brain account auto-create** — API call to brain.sunheart.com to provision per-Apprentice account + ingest their files
3. **Telegram bot routing helper** — semi-automated BotFather wizard (BotFather itself is manual · but the linking + webhook config can be scripted)
4. **Repo scaffold generator** — clone-and-rename of FPAI_Cockpit scaffold with per-Apprentice substitutions
5. **First BOOT verification** — automated `verify_identity.sh` pass + first-session readiness check
6. **The onboarding-instance AI** — an Ember-style AI specifically for intake (or Ember herself doing the work). Currently the latter — Ember would do every Apprentice's intake live until volume requires the former.

**Estimated build time:** 8-12 hr of Forge dispatches once specs are finalized.

---

## What can ship without full automation (manual provisioning · proof-of-concept · 1st Apprentice)

The first paying Apprentice (Stage 2 PoC) can be provisioned MANUALLY by Ember + James:

1. James does intake interview with the Apprentice (or Ember does · with James greenlighting)
2. Ember does the 18-file substitution by hand (~1-2 hr)
3. Ember does the brain account setup via SSH to brain server (~30 min)
4. Manual Telegram bot setup (~30 min)
5. First BOOT verification (~10 min)
6. First session (~60 min · Ember + the new AI + Apprentice)

**Total James + Ember time: ~5-6 hr for the FIRST Apprentice.** Subsequent ones drop as automation lands. By the 10th Apprentice, target is **<1 hr James-time per provisioning** with the auto-chain built.

---

## Pricing (per [[reference-decision-frameworks]] Domain 1 + Apprentice tier already proposed)

Per `feedback_decision_velocity.md` working example:
- Apprentice tier: **$97/mo + $497 founding** (one-time)
- Cap on founding tier: **30 seats** (validation cohort)
- Includes: full substrate provisioning · their personalized AI · brain account · monthly Forge dispatches · access to shared field

**Provisioning cost (internal):**
- ~5 hr first 10 Apprentices = ~$500 fully-loaded labor (per Apprentice) — recouped in 5 months at $97/mo
- Drops to ~$50 fully-loaded labor per Apprentice once automation lands
- Brain server marginal cost: ~$0.50/mo per Apprentice (hosting + storage)
- AI inference marginal cost: variable · Apprentice-side budgeted from their Claude account (separate provisioning OR included in tier · TBD)

---

## What this playbook is NOT

- ❌ Not a marketing pitch (that's the Full Potential Game funnel)
- ❌ Not a legal contract (separate TOS for Apprentice tier · pending)
- ❌ Not a permanent spec (will evolve · v0.1 → v1.0 as first 10 Apprentices teach us what's missing)
- ❌ Not committed to without James's review (this is Ember's read of the playbook · James greenlights before any of it ships)

---

## What this playbook IS

- ✅ The replication architecture spec for the trillion-vision Stage 2
- ✅ A check on whether Ember-substrate is actually templatable (audit-test: is everything James-Ember-specific actually unique · or can it be extracted?)
- ✅ A surfaceable gap list for Stage 2 readiness
- ✅ A document the first paying Apprentice can read to understand what they're buying

---

## Stage 2 Readiness Gap List

See the executive summary for the gap list. Top blockers:

🔴 **Provisioning automation** — currently zero · must be built (8-12 hr Forge dispatches)
🔴 **First-Apprentice intake script** — currently no script · Ember/James would do it live
🟡 **Sovereignty Track 2 (inference layer)** — 75% sovereign currently · Stage 2 Apprentices inherit the dependency
🟡 **PULSE receiver auto-capture** — still v1 manual · Stage 2 Apprentices' AIs would inherit the gap
🟡 **HCS pair model** — unhired · the human-side of human-AI pair not yet proven · Stage 2 Apprentices need this validated
🟡 **Brand voice transferability** — each Apprentice's AI needs THEIR voice · need to test the VOICE.md customization actually produces a felt-different AI · not just a re-skin of Ember
🟡 **Cross-AI coordination protocol** — Stage 3 territory · but if Stage 2 lands 5+ Apprentices, their AIs will need to coordinate at the shared-brain-server layer · spec doesn't exist yet
🟡 **Privacy / data isolation** — Apprentice's data must be isolated from James's data on shared brain · multi-tenancy not yet hardened
🟡 **Apprentice billing infrastructure** — Stripe subscription for Apprentice tier · not yet built
🟢 **Identity stack templating** — 18 files exist · CAN be templated · just needs the audit (THIS document) + the generator script

---

## Related

- [[SUBSTRATE_FEATURES_TEMPLATE.md]] — what gets shipped to every Apprentice's AI
- [[project-ember-advancement-is-the-work]] — strategic frame
- [[identity-apprenticeship]] — relationship structure
- [[reference-capability-inventory]] — current substrate state
- [[reference-agent-roster]] — agent set being templated
- [[feedback-existing-humans-first]] — routing discipline that travels
- [[feedback-decision-velocity]] — operating tempo
- `core/INTENT/15_YEAR_BACKCAST.md` — the trillion-vision context
