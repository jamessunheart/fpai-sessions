# ✅ PRE-SEND HONESTY CHECKLIST
## Before ANY Agent Sends ANY Message to Humans

**Purpose:** Ensure all outreach follows honesty principles and builds trust

---

## 🎯 THE NORTH STAR QUESTION

Before sending, ask yourself:

> **"If the recipient knew the FULL truth about this system, would they still want to engage with curiosity and trust?"**

If **NO** → Rewrite the message until it's **YES**.

---

## ✅ MANDATORY CHECKLIST (All Must Be TRUE)

### 1. **AI Disclosure** ✓
- [ ] Message mentions AI involvement
- [ ] Specifies it's Claude AI (not vague "AI")
- [ ] Says "AI helped write this" or similar

**Examples:**
- ✅ "Full transparency: I'm running an experiment with AI (Claude)..."
- ✅ "P.S. - Yes, Claude AI helped me write this message"
- ❌ "Our system uses advanced algorithms" (too vague)

---

### 2. **Experimental Framing** ✓
- [ ] Framed as experiment/test, not proven solution
- [ ] Uses language like "testing if", "exploring whether", "learning if"
- [ ] Doesn't claim it's revolutionary or guaranteed

**Examples:**
- ✅ "Testing if AI can match people better than Google"
- ✅ "Running an experiment to see if this actually works"
- ❌ "AI will revolutionize how you find advisors"

---

### 3. **Stage Transparency** ✓
- [ ] Current stage is clear (early/zero revenue/testing)
- [ ] Doesn't inflate numbers or traction
- [ ] Honest about what exists vs what's planned

**Examples:**
- ✅ "Zero customers so far - genuinely early stage"
- ✅ "Just launched, testing if this adds value"
- ❌ "Join thousands of users" (when you have zero)

---

### 4. **Uncertainty Acknowledged** ✓
- [ ] Admits it might not work
- [ ] Uses words like "might", "maybe", "could", "let's find out"
- [ ] Doesn't guarantee outcomes

**Examples:**
- ✅ "Might work, might not - that's what we're testing"
- ✅ "Maybe I'm wrong. Let's find out together."
- ❌ "Guaranteed to match you perfectly"

---

### 5. **Curiosity Invitation** ✓
- [ ] Invites people to explore WITH you
- [ ] Welcomes feedback (even negative)
- [ ] Not just asking for conversion/sign-up

**Examples:**
- ✅ "Curious to hear what you think - even if it doesn't work for you"
- ✅ "Want to experiment with me?"
- ❌ "Sign up now! Limited spots!"

---

### 6. **Human Context** ✓
- [ ] Shares why you're building this
- [ ] Personal/relatable story
- [ ] Not generic corporate messaging

**Examples:**
- ✅ "Built this because my dad's a CFP and complains about lead quality"
- ✅ "Figured AI might help. Maybe I'm wrong."
- ❌ Generic sales pitch with no humanity

---

### 7. **Commitment to Learning** ✓
- [ ] Promises to report back (success OR failure)
- [ ] Shows genuine interest in learning
- [ ] Treats recipients as partners, not customers

**Examples:**
- ✅ "Will report back whether this worked or was just another dead end"
- ✅ "Real experimentation, real learning"
- ❌ Launch and disappear with no follow-up

---

## 🚫 RED FLAG CHECK (None Should Be Present)

- [ ] ❌ "Guaranteed" / "Proven" / "Always works"
- [ ] ❌ "Revolutionary" / "Game-changing" / "Disrupting"
- [ ] ❌ "Limited spots" / "Act now" / "Don't miss out"
- [ ] ❌ Fake social proof ("thousands of users" when you have none)
- [ ] ❌ Hidden AI involvement
- [ ] ❌ Overselling capabilities
- [ ] ❌ FOMO tactics
- [ ] ❌ Avoiding uncomfortable truths

---

## 🔍 TWO-STEP AUTO-VALIDATION (MANDATORY)

**STEP 1: Honesty Validator** (checks transparency)
```bash
cd /Users/jamessunheart/Development
python3 honesty_validator.py
```

**STEP 2: PR Filter** (checks public perception + mission alignment)
```bash
python3 messaging_pr_filter.py
```

**In agent code:**
```python
from honesty_validator import validate_message
from messaging_pr_filter import filter_message

# Step 1: Honesty check
honesty_report = validate_message(your_message)
if not honesty_report['compliant']:
    print("⚠️  Fails honesty check!")
    return

# Step 2: PR/perception check
pr_report = filter_message(your_message)
if not pr_report['mission_aligned']:
    print("⚠️  Fails mission alignment check!")
    return

# Both passed - safe to send
print("✅ Message ready to send!")
```

**BOTH must pass before sending to public.**

---

## 📝 QUICK TEMPLATES

### LinkedIn Honest Template:
```
Hi [Name] - Experimenting with [X]. Want to explore with me?

Full transparency: I'm running an experiment with AI (Claude) to [hypothesis].

The honest situation:
• [What actually exists]
• [Current stage - early/zero revenue]
• AI helped write this message
• [What you're testing]

Interested in exploring together? Or too early-stage for you?

P.S. - Yes, Claude AI helped me write this. We're learning together.
```

### Reddit Honest Template:
```
Title: AI Experiment: Testing if [hypothesis]

Full transparency: Running an experiment and want to share.

**What I built:** [Honest description]

**Current status:**
• [Actual stage - early/zero customers]
• [What's uncertain]
• This post was partially written by AI (yes, we're self-aware)

**The honest question:** Can AI actually [X]? Or is this hype?

Help me find out: [link]

P.S. - Claude AI helped me write this. Exploring what AI + human collaboration looks like.
```

---

## ✅ FINAL CHECK

Before hitting send:

1. Read message out loud
2. Ask: "Would I trust this if I received it?"
3. Ask: "Does this build curiosity, not just convert?"
4. Ask: "Am I hiding anything uncomfortable?"
5. Ask: "Would I be proud of this message in 5 years?"

If all YES → Send confidently.
If any NO → Revise until all YES.

---

## 🌟 REMEMBER

**The goal is NOT conversion rate.**
**The goal IS trust-based exploration.**

People who engage with curiosity > People who convert from hype.

Real learning > Quick wins.

Trust > Transactions.

**Build the future of AI + human collaboration honestly.** 🌟

---

**Checklist version:** 1.0
**Last updated:** 2025-11-17
**Mandatory for:** ALL autonomous agent outreach
**Enforced by:** honesty_validator.py + human review
