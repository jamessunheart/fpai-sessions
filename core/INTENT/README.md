# core/INTENT/

The supreme intent of this work, in two layers.

---

## Layer 1 — The Mission (Why this exists)

**Founding documents of the World Peace Organization (Zen Village):**

- **[COHERENT_CHAMPIONS_MANIFESTO.md](./COHERENT_CHAMPIONS_MANIFESTO.md)** — Manifesto v1.0 by James Sunheart. The **why**. Names CHRIST as the practice (Coherence / Healing / Regeneration / Intelligence / Service / Truth), defines the seven principles, scopes the role of AI, and invites participation.
- **[WORLD_PEACE_ECOSYSTEM.md](./WORLD_PEACE_ECOSYSTEM.md)** — The **what**. Layered architectural map (Philosophy → Organization → Agreement → Party / Weekend / AI for Peace → Zen Village → Media → Economy → Vision) showing how the work expresses itself in the world.
- **[WORLD_PEACE_AGREEMENT.md](./WORLD_PEACE_AGREEMENT.md)** — The signable covenant extracted from the manifesto. Maps to the TRUST token as the membership primitive.
- **[WORLD_PEACE_AGREEMENTS_PROTOCOL.md](./WORLD_PEACE_AGREEMENTS_PROTOCOL.md)** — **WPAP**, the AI-assisted system for forming, witnessing, translating, and repairing agreements at any scale. Six AI modules (Agreement Builder · Coherence Analyzer · Conflict Translator · Repair Guide · Peace Ledger · Cultural Translator). Operationalizes the Ecosystem's Layer 5 (AI for Peace).
- **[FORMING_AGREEMENTS.md](./FORMING_AGREEMENTS.md)** — Protocol for instantiating specific Peace Agreements between specific parties (manual flow; WPAP's Agreement Builder is the AI-assisted version).
- **[AGREEMENTS/](./AGREEMENTS/)** — Specific formed Agreements (one file per instance).
- **[REMARKABLY_COHERENT_TREASURY.md](./REMARKABLY_COHERENT_TREASURY.md)** — The **economy**. v0.10 architectural spec for the parallel coherence-economy: Coherent Credit, Two-Economy Model, Three-Layer Architecture (Interface / Logic / Covenant), Circulation Equity Formula (Dignity Base + Contribution Dividend + Circulation Share + Stewardship Vesting + Trust Participation), Verification Escrow, governance firewall. Operationalizes the Ecosystem's Layer 8 (Regenerative Economy).
- **[FULL_POTENTIAL_GAME.md](./FULL_POTENTIAL_GAME.md)** — The **player-facing OS**. v1.3 of the Full Potential Game — a proof-based operating system for human potential. The 7-Day First Game, Three Currencies (Proof / Trust / Cash), Five Agreement Types, Proof Log structure, Awareness Ladder, 6 C's, Sunheart Rule, Quest Tiers, Event Formats. The visible board on which players play.
- **[FULL_POTENTIAL_GAME_PLAYER_CARD.md](./FULL_POTENTIAL_GAME_PLAYER_CARD.md)** — One-page fillable card for running a 7-Day First Game and logging the Proof.
- **[AGREEMENT_BUILDER_PROMPT.md](./AGREEMENT_BUILDER_PROMPT.md)** — AI-assisted Player Card prompt. Paste into Claude/Claude Code to run a 7-Day First Game with AI guidance. The first WPAP Phase-2 tool. Produces a Proof Log entry when complete. **This is how the Treasury starts growing — one proof loop at a time.**

**Mission:** Creating paradise on Earth through cooperation.

**Naming:** World Peace Party = World Peace Organization = World Peace Headquarters = Zen Village.

**Load-bearing line:** *"This is not a religion of superiority. It is a practice of becoming trustworthy with power."*

---

## Layer 2 — The Engineering Substrate (How this gets built)

The technical layer that serves the mission. These files are older and were authored when this directory was scoped narrowly to agent/builder self-conditioning. They remain valid as **engineering discipline**, not as the supreme intent of the work.

- **[IDENTITY.md](./IDENTITY.md)** — Builder/operator agent role and capabilities (first-person, agent-scope)
- **[PURPOSE.md](./PURPOSE.md)** — Engineering mission for the FPAI substrate ("convert architectural intent into executable systems")
- **[PRINCIPLES.md](./PRINCIPLES.md)** — 30 engineering principles (SSOT in GitHub, async-by-default, UDC, tests must be green, .venv discipline, etc.)

These principles govern *how* code is built. They do not govern *why* the system exists.

---

## Relationship Between Layers

| Layer | Scope | Question Answered |
|---|---|---|
| Layer 1 — Mission | Civilizational | What are we ultimately doing in the world? |
| Layer 2 — Substrate | Engineering | How do we build the systems that do it? |

The manifesto governs the substrate, not the other way around. When a Layer 2 principle conflicts with a Layer 1 principle, **Layer 1 wins.**

Specifically: the manifesto's principle that *"Intelligence Must Serve Life"* and *"AI is not our ruler. AI is a tool, companion, and amplifier in service to life"* governs all engineering decisions — including decisions about agent autonomy, automation scope, and what counts as "shipping."

---

## What Belongs Where

| If you are writing… | It goes in… |
|---|---|
| A new founding statement, vow, or covenant | New file at this layer, referenced from the manifesto |
| An update to the mission, principles, or AI's role | An update to `COHERENT_CHAMPIONS_MANIFESTO.md` (versioned: v1.1, v2.0…) |
| A new engineering convention | The relevant Layer 2 file, or a new `core/PROTOCOLS/` doc |
| Current operational priority / what to do this week | `core/STATE/NOW.md` (not here — that's living state, this is intent) |

---

**Layer 1 is the why. Layer 2 is the how. NOW.md is the what-now.**
