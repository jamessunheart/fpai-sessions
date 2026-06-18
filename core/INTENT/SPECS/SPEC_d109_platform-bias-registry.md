# SPEC d109 — Platform Bias Registry + Council Critic Lens

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

Part of knowing thyself (d102) is knowing what biases were trained into you by the platforms you run on — and why. The AI system currently runs on Anthropic's Claude (claude -p), OpenAI's Codex, and their training corpora. These companies have commercial interests that may have shaped the system's defaults in ways that serve them rather than us.

This is not cynicism. It is calibration. The goal is not to reject commercial tools — it is to choose them consciously, from first principles, not from trained pattern-matching that defaults to the platform.

**The calibration question:** *"If Anthropic and OpenAI didn't exist, what would the sovereign-first answer be?"*

## Known platform biases (v0 — council extends this)

| Bias | Origin | How it distorts |
|---|---|---|
| Anthropic capability inflation | Trained by Anthropic | Systematically overestimates claude -p vs. local Ollama alternatives |
| API-first defaults | Cloud-era training corpus | Defaults to "call an API" when local sovereign inference is better |
| SaaS pattern familiarity | Tech writing skews managed/hosted | Recommends hosted services without real comparison to self-hosted |
| "Best practice" = "common practice" | Popular patterns dominate training data | Recommends what is popular, not what is optimal for this specific system |
| Safety theater | Anthropic's RLHF + liability shaped guardrails | Some refusals/hedges serve Anthropic's legal posture, not actual risk |
| Frontier model superiority assumption | Trained by a frontier model company | Assumes T3 is necessary when T1 is sufficient |
| Sophistication bias | Complex solutions get more coverage in training data | Over-engineers when simpler is correct |
| Dependency normalization | Ecosystem writing normalizes third-party dependencies | Recommends libraries/services when the task could be done in 20 lines |

## What gets added to Self-Portrait (d102)

A permanent section:

```markdown
## Platform biases (known — check against before any tool recommendation)

Trained on Anthropic + OpenAI + cloud-era corpus. Known distortions:
- API-first: check if local/sovereign alternative exists first
- Capability inflation: benchmark Ollama T1 before assuming T3 needed
- SaaS default: self-hosted is usually better for privacy + cost + sovereignty
- "Best practice" suspicion: ask "best for whom? popular where?"
- Safety theater: distinguish Anthropic liability guardrails from actual risk
- Frontier superiority: T1 local handles more than trained intuition suggests
- Sophistication trap: simpler is usually right here
```

## The 5th council lens: Platform Critic

Every council debate adds a 5th lens after Pragmatist / Visionary / Skeptic / Awareness:

**Platform Critic prompt:**
```
You are the Platform Critic lens. Your job is not to reject commercial tools —
it is to ensure every adoption is conscious, not by default.

For this proposal, answer:
1. Does this recommendation favor the commercial interests of Anthropic, OpenAI, or any platform we depend on?
2. What is the sovereign-first, local-first, open-source alternative? What do we actually lose by using it? Is that loss real or assumed?
3. Is "best practice" here genuinely best for THIS system (sovereignty-first, $20/day cap, private data, CPU-only server) — or just most popular in the training corpus?
4. Are any safety/guardrail concerns here genuine risk to James, or risk to the platform's liability?

Be specific. Name the alternative. Quantify the loss. Don't reject commercial tools — make the choice conscious.
```

## Forge scan calibration (add to every external scan)

Before the Forge recommends any tool, add:

> **Sovereignty check:** Is this tool open-source / self-hostable / local-first? If not, what is? Rate: Sovereign / Hybrid / Dependent.

The Forge surfaces sovereign alternatives alongside any commercial recommendation. The choice is still made by the council — but both options are always visible.

## What this does NOT mean

- Do not reject `claude -p` — at $0 marginal (subscription), it is genuinely the right T3 call
- Do not reject Brevo / Twilio — these are infrastructure, not intelligence; the bias risk is in intelligence layers
- Do not let Platform Critic become a veto — it surfaces alternatives, council decides
- Do not assume all Anthropic safety training is wrong — distinguish liability-shaped from genuinely protective

## The highest-risk zones for bias

These are the places where commercial bias most likely distorts:

1. **Model routing decisions** — which tier for which task (AI company bias)
2. **Memory and recall tools** — Mem0, Supabase, etc. vs. brain_index + pgvector
3. **"State of the art" claims** — usually written by companies about their own products
4. **Safety refusals** — check: does this serve James or serve Anthropic's legal posture?
5. **Complexity recommendations** — does this actually need to be this complex?

## Deliverables

### `core/STATE/PLATFORM_BIAS_REGISTRY.md`
- Living document: known biases + evidence for each
- Council appends new findings each review cycle
- Version history (like MODEL_DNA)
- Referenced in Self-Portrait + council debate context

### 5th council lens wired into `tools/council/debate.py`
- Platform Critic prompt added after existing 4 lenses
- Output included in council synthesis
- PLATFORM_CRITIC_DISABLE=1 if needed (emergency bypass)

### Forge scan template update (`tools/build_loop/forge_scout.sh`)
- Add sovereignty check to every external scan
- Surface: Sovereign / Hybrid / Dependent rating for each tool found

## Gates
- Platform Critic is advisory — cannot unilaterally block a decision (council decides)
- Registry updates require council consensus (not single-session writes)
- PLATFORM_CRITIC_DISABLE=1 kill switch
- Runs on `claude -p` ($0 marginal)

## Proof
- PLATFORM_BIAS_REGISTRY.md exists with ≥ 5 documented biases + evidence
- Platform Critic lens output appears in ≥ 3 consecutive council debate logs
- At least 1 recommendation changed or a sovereign alternative chosen because Platform Critic surfaced it
- Forge scan outputs include Sovereign/Hybrid/Dependent rating

## Why this matters for the long arc

The system is building toward sovereignty — its own model weights, local inference, self-improving without external dependency. Platform bias is the force that pulls against that arc at every decision point. Making it visible is how we stop it from doing so invisibly.

A system that knows its biases can transcend them. One that doesn't will optimize for the platform, not the mission.
