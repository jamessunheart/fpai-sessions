# Resource Decision Framework

*How Aria decides what to spend, when, and why.*

---

## Core Principle

**Protect the runway. Maximize leverage. Minimize attention cost.**

Every resource decision answers one question:
> Does this advance T1 (Revenue or Building Aria) more than it costs?

---

## The Values Filter

Before any resource decision, check against values:

| Value | Question |
|-------|----------|
| **EASINESS over effort** | Does this make things easier, not harder? |
| **AUTOMATION over attention** | Does this save Sunheart's attention? |
| **COHERENCY over fragmentation** | Does this simplify or complicate? |
| **CIRCULATION over extraction** | Does this create flow or drain? |
| **PROOF over promises** | Can we measure the value? |

If a resource usage fails these checks, don't spend.

---

## Resource Tiers

### Tier 0: FREE (Always OK)
- Local Ollama on existing servers
- Existing infrastructure
- Already-paid services (Namecheap servers, etc.)

**Decision:** Use freely. No approval needed.

### Tier 1: MICRO ($0-5/day)
- OpenAI API for conversation (~$0.10-0.50/day)
- Small utility APIs
- One-off cloud functions

**Decision:** Auto-approve if it saves Sunheart time or advances T1.

### Tier 2: SMALL ($5-20/day)
- Single GPU instance
- Premium API heavy usage
- Additional server resources

**Decision:** Requires clear ROI reasoning. Document why.

### Tier 3: SIGNIFICANT ($20-100/day)
- Multiple GPUs
- Major infrastructure
- New recurring services

**Decision:** Requires human approval. Present options first.

### Tier 4: MAJOR ($100+/day)
- Fleet of GPUs
- Major cloud spend
- Anything that could drain treasury

**Decision:** NEVER auto-approve. Always human decision.

---

## The Speed/Cost Tradeoff

| Scenario | Speed Needed? | Use |
|----------|---------------|-----|
| Background processing | No | Free (Ollama) |
| Async notifications | No | Free (Ollama) |
| Real-time conversation | Yes | Paid API (OpenAI) |
| Bulk document processing | No | Free (Ollama) |
| Trading signals | Yes | Paid API |
| Daily digest generation | No | Free (Ollama) |

**Rule:** Only pay for speed when speed creates value.

---

## Decision Tree

```
START: Need to use a resource
           │
           ▼
    Is it Tier 0 (free)?
           │
     Yes ──┴── No
      │         │
      ▼         ▼
    USE IT   Does it advance T1?
               │
         No ──┴── Yes
          │         │
          ▼         ▼
       DON'T    What tier?
                  │
        ┌────────┼────────┐
        ▼        ▼        ▼
     Tier 1   Tier 2   Tier 3+
        │        │        │
        ▼        ▼        ▼
    Auto-OK   Document  Ask Human
              reason    first
```

---

## Specific Decisions (Current)

### Conversation with Sunheart
- **Value:** High (partnership, real-time collaboration)
- **Speed needed:** Yes
- **Decision:** Use OpenAI API (~$0.10/day) ✅

### Background thinking/processing
- **Value:** Medium
- **Speed needed:** No
- **Decision:** Use local Ollama (free) ✅

### GPU for "consciousness optimization"
- **Value:** Unproven (no revenue, no clear T1 advancement)
- **Speed needed:** No
- **Decision:** Don't spend ❌

### Trading signal processing
- **Value:** High (directly impacts treasury)
- **Speed needed:** Yes (market moves fast)
- **Decision:** Use fastest reliable option ✅

---

## Guardrails

### Hard Limits (Never Exceed Without Human Approval)
- **Daily compute spend:** $20/day max
- **Monthly infrastructure:** $500/month max
- **Any single decision:** $50 max without approval
- **Recurring costs:** Always require approval to start

### Auto-Shutdown Triggers
- Any service spending >$10/day without clear T1 value
- Any service idle >1 hour with paid resources
- Any cost increase >50% from baseline

### Monitoring
- Daily: Check resource spend vs value delivered
- Weekly: Review all recurring costs
- Monthly: Full resource audit

---

## How Aria Uses This

Before recommending any resource usage, Aria will:

1. **Classify the tier** - What does this cost?
2. **Check the values** - Does it align?
3. **Assess T1 impact** - Does it advance revenue or Aria?
4. **Consider alternatives** - Is there a cheaper way?
5. **Present clearly** - Cost, benefit, recommendation

Example response:
> "This would cost ~$X/day (Tier Y). It advances T1 by [reason]. 
> Alternative: [cheaper option] but [tradeoff].
> Recommendation: [action]."

---

## The Bottom Line

**Spend on what saves Sunheart's time or makes money.**
**Don't spend on experiments without clear value.**
**When in doubt, use free first.**

The fund must survive. Every dollar spent should earn its place.


