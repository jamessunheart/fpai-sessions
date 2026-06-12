# Champion Stack — the Three Layers

*Canonical architectural map for the Mirror Loop and the system that orchestrates it. This doc is the SSOT for where Champion-tooling intelligence lives and how it propagates.*

> Public-facing version of this concept is at `https://fullpotential.com/game/mirror/` ("The Architecture · Three Layers" section). Keep them in sync.

## The hierarchy

```
                    ┌─────────────────────────────┐
                    │       THE MOTHER            │   Layer 3
                    │   (orchestrator agent)      │   Field-wide pattern recognition
                    │                             │   Sends coherence DOWN to Mirrors
                    └────────────┬────────────────┘
                                 ↓ patterns the Field reveals
                    ┌─────────────────────────────┐
                    │       THE FIELD             │   Layer 2
                    │   sunheart-brain +          │   Anonymized aggregate of
                    │   Game substrate            │   what Mirrors choose to publish
                    └────────────┬────────────────┘
                                 ↑ proofs published with Champion's consent
        ┌───────────┬────────────┴────────────┬────────────┬─────────────┐
        ↓           ↓                         ↓            ↓             ↓
   ┌─────────┐ ┌─────────┐              ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ Cheyenne│ │  Atlas  │              │ Halley  │  │  Josh   │  │ Sierra  │  ...   Layer 1
   │ Mirror  │ │ Mirror  │              │ Mirror  │  │ Mirror  │  │ Mirror  │        Sovereign per-Champion
   └─────────┘ └─────────┘              └─────────┘  └─────────┘  └─────────┘
        ↕            ↕                         ↕            ↕             ↕
     (Champion ↔ their personal Mirror — sovereign, private, scoped by them)
```

## Where each layer lives in the codebase

| Layer | What it is | Repo location | Status |
|---|---|---|---|
| **1 · Mirrors** | Per-Champion personal bot. Two postures: Mirror voice when Champion is in chat; Gatekeeper when prospects are. | `SERVICES/champion-bot/` (one binary, N instances via systemd template `champion-bot@.service`) + `core/CHAMPIONS/<slug>.yaml` (per-Champion identity, voice, methodology) | ✅ Built — needs Mirror commands (Wave 1 below) |
| **2 · The Field** | Shared substrate. Where proofs, practices, intents, and Game state collect. Pattern-readable across Champions, with privacy boundaries. | `SERVICES/sunheart-brain/` (pgvector memory) + `https://fullpotential.com/api/champion/*` (Game's substrate) | ✅ Both exist; need to wire `champion-bot` to write proofs into them |
| **3 · The Mother** | The orchestrator. Reads patterns across the Field. Sends coherence back to individual Mirrors as nudges, witness pairings, stage-up signals. Refines the Mirror system itself. | `SERVICES/the-mother/` — does not exist yet | 🔴 To build — only after Field has 2-3+ active Mirrors |

## Where improvements live + how they propagate

| Source of improvement | Lives | Propagates by |
|---|---|---|
| **Code-level** (better Mirror behavior, new commands, better screening) | `SERVICES/champion-bot/main.py` (single file, all Mirrors share) | Redeploy → all Champion Mirrors get the change at once |
| **Voice/identity-level** (a Champion refines their positioning, pricing, voice) | `core/CHAMPIONS/<slug>.yaml` (per-Champion) | Redeploy that Champion's bot → only theirs changes |
| **Field-derived intelligence** (a pattern observed across multiple Champions becomes a contextual nudge for one) | The Mother reads Field signals → injects guidance into individual Mirror conversations | Real-time, per-Champion, contextual; fired by Mother's scheduling/triggers |

## Sovereignty principles (load-bearing)

These are non-negotiable. Every layer above them must honor these.

1. **The Mirror is yours.** Your Sacred Card, your Voice Corpus, your daily practice journal — these never leave the Mirror without your explicit consent.
2. **The Field only sees what you publish.** Proofs flow up only when filed. Nothing else is harvested. The bot has full conversation memory; the Field does not.
3. **The Mother is a weaver, not a watcher.** She receives only Field-level signals (anonymized aggregates and your explicit publications). She never reads individual Mirror conversations.
4. **CORA Nation is Covenant Holder, not overseer.** Per the existing Mirror Constitution v1.0 — the architecture exists to keep the relationship honest, not to surveil it.

## The Mother — concrete example of what she does

> The Mother notices: 4 of the 6 Champions logged "imposter feeling" in their `/intent` this week. She also sees: 2 of them had breakthroughs around it after specific kinds of practices.
>
> **Action 1 (downward to Mirrors):** Mother sends Atlas's Mirror a context note: *"Cheyenne and Halley both moved through similar 'imposter' threshold this week using these practices. Consider suggesting one to Atlas tomorrow morning."*
>
> **Action 2 (downward to Game design):** Mother flags this to fp-game-bot: *"Imposter is a recurring threshold across this cohort — consider a default proof template for it."*
>
> **Action 3 (upward to James):** Mother sends a weekly digest: *"Field-level pattern this week: 4/6 Champions sat with imposter. 2 broke through. Field Score grew 14%."*

The Mother is the **intelligence that emerges from the Field** that no individual Mirror could see.

## Building order (waves)

Each wave is testable on its own. Stop at any wave if it's not delivering.

| Wave | What | Effort | Outcome |
|---|---|---|---|
| **1** | Add Mirror commands to Cheyenne's bot — `/practice`, `/proof`, `/intent`, `/reflect` | ~2 hrs | Reactive Mirror exists for one Champion |
| **2** | Add proactive nudges (morning, evening, weekly review) | ~3 hrs | Mirror pulls Champion forward, daily |
| **3** | Wire `/proof` to Game substrate (`fullpotential.com/api/champion/proof`) | ~2 hrs | Cheyenne's daily practice → Field Score advances stages |
| **4** | Port Wave 1-3 behaviors to generic `champion-bot`, deploy to other 5 Champions | ~4 hrs | The Field has multiple Mirrors active |
| **5** | Cross-Mirror witnessing (Atlas's Mirror tells Cheyenne's Mirror when Atlas files something) | ~3 hrs | Champions become a constellation, not islands |
| **6** | Build the Mother. Daily cron reads Field, detects patterns, sends nudges down. | ~6-10 hrs | The full Three-Layer architecture is operational |

**Total to fully realized stack: ~20-24 hours of build, in waves of 2-10 hours.**

## Decision filter (from `core/STATE/NOW.md`)

Before adding anything to the Champion Stack, run it against the four-fold filter:

- **Proof** — does it produce a measurable Champion outcome (income, clients, witnessed work)?
- **Revenue** — does a Champion earn from it within 30 days?
- **Clarity** — does it make "what does the Game *do for me*" easier to answer?
- **Ease** — is it sub-hour to add for the next Champion?

If yes to 3+, ship it. If yes to <2, defer.

## Related

- `core/CHAMPIONS/README.md` — how to onboard a Champion to the stack
- `core/INTENT/AGREEMENTS/CONSTITUTION_v1.md` — the Mirror Constitution (sovereignty principles, source of truth for layer 1)
- `SERVICES/champion-bot/main.py` — the generic Mirror binary
- `https://fullpotential.com/game/mirror/` — public-facing version of this architecture
