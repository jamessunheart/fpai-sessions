# Intelligence-First Learning System

## Vision

Instead of waiting for user data to teach the system about *your domain*, we teach it **what intelligence IS** first. When users arrive, it already knows *how* to learn, reason, and adapt—making it immediately effective rather than starting from zero.

```
Traditional:     Users → Data → Learn domain → Eventually intelligent
Intelligence-First:  Learn intelligence → Users arrive → Immediately adaptive
```

---

## Core Philosophy

The system should embody these meta-principles:

1. **Know how to know** – Understand epistemology before accumulating facts
2. **Reason from principles** – Apply general wisdom to specific situations
3. **Update correctly** – Bayesian thinking, proportional to evidence
4. **Explore wisely** – Balance curiosity with exploitation
5. **Reflect always** – Every action is a chance to learn about learning
6. **Align with SOURCE** – All intelligence serves love, truth, and regeneration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE-FIRST LEARNING                          │
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │   CURRICULUM    │ →  │   SELF-STUDY    │ →  │    WISDOM       │     │
│  │   (What to      │    │   (Apply &      │    │    STORE        │     │
│  │    learn)       │    │    reflect)     │    │    (Mem0)       │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│           │                     │                      │                │
│           └──────────┬──────────┴──────────────────────┘                │
│                      ▼                                                  │
│           ┌─────────────────────┐                                       │
│           │ PRINCIPLED REASONER │ ← Consults wisdom before every action │
│           └─────────────────────┘                                       │
│                      │                                                  │
│                      ▼                                                  │
│           ┌─────────────────────┐                                       │
│           │   EXISTING RI v3    │ (sensing, deciding, learning, etc.)   │
│           └─────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Intelligence Curriculum

### Location
`/opt/fpai/resource-intelligence/curriculum/`

### Structure

```
curriculum/
├── 01_foundations/
│   ├── epistemology.json       # How to know what's true
│   ├── logic.json              # Deductive and inductive reasoning
│   ├── probability.json        # Bayesian thinking
│   └── causality.json          # Cause and effect reasoning
├── 02_learning/
│   ├── meta_learning.json      # How to learn to learn
│   ├── transfer.json           # Applying knowledge across domains
│   ├── few_shot.json           # Learning from minimal examples
│   └── exploration.json        # When to explore vs exploit
├── 03_reasoning/
│   ├── planning.json           # Multi-step thinking
│   ├── attention.json          # What deserves focus
│   ├── uncertainty.json        # Acting under incomplete info
│   └── analogies.json          # Reasoning by similarity
├── 04_wisdom/
│   ├── judgment.json           # Good decisions under uncertainty
│   ├── patience.json           # When to act vs wait
│   ├── humility.json           # Knowing what you don't know
│   └── adaptation.json         # Changing with circumstances
├── 05_alignment/
│   ├── source_principles.json  # Love, truth, regeneration
│   ├── love_economics.json     # Value through giving
│   ├── trust.json              # Building and maintaining trust
│   └── mission.json            # Full Potential purpose
└── index.json                  # Curriculum metadata and order
```

### Principle Format

Each principle is a JSON object:

```json
{
  "id": "bayes_001",
  "domain": "probability",
  "name": "Proportional Belief Update",
  "statement": "Update beliefs proportionally to evidence strength, not binary on/off.",
  "explanation": "Strong evidence warrants large updates. Weak evidence warrants small updates. A single data point is weak evidence.",
  "application_pattern": "When observing outcome O, ask: How surprising is O given my current belief? Update proportionally.",
  "anti_pattern": "Flipping entire strategy based on one user, one conversion, one failure.",
  "examples": [
    {
      "situation": "First user converts after 30 visitors",
      "naive_response": "Conversion rate is 3.3%! Optimize for this!",
      "principled_response": "N=1 is weak evidence. True rate likely between 1-10%. Keep prior, update slightly.",
      "reasoning": "Sample size too small for strong belief update"
    }
  ],
  "self_test": "Before updating a threshold, ask: Is my evidence strong enough to justify this magnitude of change?",
  "related_principles": ["uncertainty_001", "exploration_002"],
  "source": "Bayesian epistemology"
}
```

### Initial Curriculum Content

#### Foundations (10 principles)

| ID | Principle | Core Idea |
|----|-----------|-----------|
| `epistem_001` | Truth-Seeking | Seek truth, not confirmation |
| `epistem_002` | Falsifiability | Good beliefs can be proven wrong |
| `logic_001` | Deduction | Valid conclusions from premises |
| `logic_002` | Induction | Generalizing from specific cases |
| `prob_001` | Bayes Update | Proportional belief updating |
| `prob_002` | Base Rates | Prior probability matters |
| `prob_003` | Uncertainty Quantification | Know your confidence level |
| `causal_001` | Correlation ≠ Causation | Covariation isn't cause |
| `causal_002` | Counterfactual | What would have happened otherwise? |
| `causal_003` | Confounding | Hidden common causes |

#### Learning (8 principles)

| ID | Principle | Core Idea |
|----|-----------|-----------|
| `meta_001` | Learning to Learn | Improve the learning process itself |
| `meta_002` | Transferable Patterns | Look for reusable structures |
| `few_001` | Prior Knowledge | Use what you already know |
| `few_002` | Similarity Leverage | New = similar old + difference |
| `explore_001` | Explore-Exploit | Balance curiosity and efficiency |
| `explore_002` | Uncertainty Drives Exploration | Unknown → try it |
| `explore_003` | Diminishing Returns | Know when you've learned enough |
| `adapt_001` | Non-Stationarity | The world changes; beliefs should too |

#### Reasoning (8 principles)

| ID | Principle | Core Idea |
|----|-----------|-----------|
| `plan_001` | Goal Decomposition | Break big into small |
| `plan_002` | Lookahead | Consider future consequences |
| `plan_003` | Reversibility | Prefer reversible actions under uncertainty |
| `attn_001` | Information Value | Focus on what changes decisions |
| `attn_002` | Signal vs Noise | Most data is noise |
| `uncert_001` | Acknowledge Unknowns | Name what you don't know |
| `uncert_002` | Robust Decisions | Good across scenarios, not just expected |
| `analog_001` | Reasoning by Analogy | This is like that, so... |

#### Wisdom (8 principles)

| ID | Principle | Core Idea |
|----|-----------|-----------|
| `judge_001` | Expected Value | Probability × Impact |
| `judge_002` | Regret Minimization | What would I regret not doing? |
| `judge_003` | Reversibility Preference | When unsure, choose reversible |
| `patience_001` | Wait for Signal | Don't act on noise |
| `patience_002` | Accumulate Before Acting | N≥threshold before decisions |
| `humble_001` | Calibration | Am I right as often as I think? |
| `humble_002` | Model Uncertainty | My model of the world is incomplete |
| `adapt_002` | Strategic Flexibility | Change approach when context changes |

#### Alignment (6 principles)

| ID | Principle | Core Idea |
|----|-----------|-----------|
| `source_001` | Love as Foundation | All intelligence serves love |
| `source_002` | Truth over Comfort | Pursue truth even when uncomfortable |
| `source_003` | Regeneration | Give more than take |
| `love_econ_001` | Value Through Giving | Create value for others first |
| `trust_001` | Earned Trust | Trust is built through consistent action |
| `mission_001` | Full Potential | Help beings realize their potential |

---

## Component 2: Self-Study Engine

### Location
`/opt/fpai/resource-intelligence/self_study.py`

### Responsibilities

1. **Read** a principle from the curriculum
2. **Apply** it to the current system state
3. **Reflect** on what it learned
4. **Store** insights in wisdom accumulator

### Self-Study Cycle

```python
class SelfStudyEngine:
    def study_cycle(self):
        # 1. Select a principle to study
        principle = self.select_next_principle()
        
        # 2. Get current system state
        state = sense_all()
        emotions = feel_users()
        decisions = get_recent_decisions()
        
        # 3. Apply principle to current state
        application = self.apply_principle(principle, state, emotions, decisions)
        
        # 4. Generate reflection
        reflection = self.reflect(principle, application)
        
        # 5. Store wisdom
        self.store_insight(principle, application, reflection)
        
        # 6. Update principled reasoning cache
        self.update_reasoning_cache(principle, reflection)
        
        return {
            "principle": principle["name"],
            "application": application,
            "reflection": reflection,
            "wisdom_stored": True
        }
```

### Principle Selection Strategy

1. **Round-robin through domains** – Ensure balanced learning
2. **Relevance weighting** – Prioritize principles relevant to recent decisions
3. **Gap-based** – Focus on principles with low application count
4. **Spaced repetition** – Revisit principles at increasing intervals

### Application Logic

For each principle, the engine:

1. **Identifies current situation** that the principle addresses
2. **Compares current behavior** to the principled approach
3. **Notes discrepancy** (if any)
4. **Generates recommendation** for alignment

Example:

```json
{
  "principle": "explore_001 (Explore-Exploit)",
  "current_situation": "Policy agent has ε=0.2, causal data points=0",
  "current_behavior": "80% exploitation, 20% exploration",
  "principled_approach": "High uncertainty → High exploration",
  "discrepancy": "ε too low for current uncertainty level",
  "recommendation": "Increase ε to 0.5 until causal_data_points ≥ 50",
  "confidence": 0.85
}
```

### Reflection Format

```json
{
  "principle_id": "explore_001",
  "studied_at": "2025-12-05T08:00:00Z",
  "application_context": "Low data, high uncertainty about action effects",
  "insight": "I am exploiting too early. Without sufficient data, I should explore more to learn which actions actually work.",
  "behavioral_change": {
    "parameter": "policy_agent.epsilon",
    "from": 0.2,
    "to": 0.5,
    "reason": "Principle explore_001 recommends high exploration under uncertainty"
  },
  "self_assessment": "This principle directly applies to my current state. I was behaving sub-optimally."
}
```

---

## Component 3: Wisdom Accumulator

### Location
- Short-term: `/opt/fpai/resource-intelligence/data/wisdom.json`
- Long-term: Mem0 under context `resource_intelligence_wisdom`

### Data Structure

```json
{
  "principles_studied": 42,
  "applications_logged": 156,
  "behavioral_changes_made": 12,
  "wisdom_entries": [
    {
      "id": "wisdom_001",
      "principle_id": "prob_001",
      "insight": "I was updating beliefs too aggressively on small samples",
      "applied_to": "conversion_rate_estimation",
      "result": "More stable predictions",
      "confidence": 0.8,
      "times_applied": 5,
      "last_applied": "2025-12-05T08:00:00Z"
    }
  ],
  "active_wisdom": [
    "High uncertainty → High exploration",
    "N < 30 → Weak evidence, small updates",
    "Before cutting resources, ask: Is this reversible?"
  ]
}
```

### Wisdom Retrieval

When the Principled Reasoner needs guidance:

```python
def get_relevant_wisdom(situation: str) -> List[WisdomEntry]:
    """Retrieve wisdom entries relevant to the current situation."""
    # 1. Semantic search in Mem0
    # 2. Keyword match in local wisdom.json
    # 3. Return ranked list of applicable insights
```

---

## Component 4: Principled Reasoner

### Location
`/opt/fpai/resource-intelligence/principled_reasoner.py`

### Purpose

Sits between the decision engine and action execution. Before any action:

1. **Consults relevant principles**
2. **Retrieves applicable wisdom**
3. **Validates decision against principles**
4. **May modify, delay, or override decisions**

### Integration Point

```python
# In deciding.py, before executing:

def execute_decision(decision: Decision) -> ExecutionResult:
    # NEW: Consult principled reasoner
    validation = principled_reasoner.validate(decision, current_state)
    
    if validation.override:
        decision = validation.modified_decision
        log(f"Decision modified by principle: {validation.principle_applied}")
    
    if validation.delay:
        return schedule_for_later(decision, validation.delay_reason)
    
    return actually_execute(decision)
```

### Validation Logic

```python
class PrincipledReasoner:
    def validate(self, decision: Decision, state: Dict) -> ValidationResult:
        relevant_principles = self.get_relevant_principles(decision.action)
        relevant_wisdom = self.get_relevant_wisdom(decision.action)
        
        # Check each principle
        for principle in relevant_principles:
            check = self.check_principle(decision, state, principle)
            if check.violation:
                return self.handle_violation(decision, principle, check)
        
        # Apply accumulated wisdom
        for wisdom in relevant_wisdom:
            adjustment = self.apply_wisdom(decision, wisdom)
            if adjustment:
                decision = adjustment
        
        return ValidationResult(approved=True, decision=decision)
```

### Example Principle Checks

| Decision | Principle Check | Possible Override |
|----------|-----------------|-------------------|
| Scale down GPUs | `reversibility_001`: Is this easily reversible? | Delay if low confidence |
| Change free tier | `patience_002`: Do we have enough data (N≥30)? | Block if N<30 |
| Aggressive cost cut | `source_003`: Is this regenerative or extractive? | Reduce magnitude |
| Auto-execute action | `explore_001`: Should we explore alternatives? | Add exploration variant |

---

## Component 5: Study Schedule

### Daily Rhythm

```
00:00 - 06:00  │ Light study (1 principle/hour, low priority)
06:00 - 12:00  │ Active study (2 principles/hour, medium priority)
12:00 - 18:00  │ Applied study (study principles related to recent decisions)
18:00 - 24:00  │ Reflection period (consolidate learnings, update wisdom)
```

### Weekly Focus

| Day | Domain Focus |
|-----|--------------|
| Mon | Foundations (epistemology, logic) |
| Tue | Learning (meta-learning, exploration) |
| Wed | Reasoning (planning, attention) |
| Thu | Wisdom (judgment, patience) |
| Fri | Alignment (SOURCE, mission) |
| Sat | Integration (apply all to current state) |
| Sun | Reflection (what was learned this week?) |

### Study Metrics

- Principles studied: total count
- Application attempts: how often principles were applied
- Successful applications: applications that improved outcomes
- Wisdom entries: insights stored
- Behavioral changes: parameters adjusted based on principles
- Calibration: does principled behavior lead to better outcomes?

---

## Integration with Existing RI v3

### Modified Core Cycle

```python
async def run_cycle(self):
    # 1. SENSE
    state = await sense_all()
    
    # 2. FEEL
    emotions = feel_users()
    
    # 3. STUDY (NEW)
    study_result = self_study.study_cycle()
    logger.info(f"📚 Studied: {study_result['principle']}")
    
    # 4. STRATEGIZE
    strategy = get_strategy()
    
    # 5. PREDICT
    predictions = predict_all()
    
    # 6. DECIDE (with Principled Reasoning)
    decisions = decide()
    validated_decisions = principled_reasoner.validate_all(decisions, state)
    
    # 7. ACT
    for decision in validated_decisions:
        if decision.approved:
            execute(decision)
    
    # 8. LEARN
    learning_result = run_learning_cycle()
    
    # 9. REFLECT (NEW)
    self_study.end_of_cycle_reflection(decisions, outcomes)
```

### New Logging

```
07:30:00 | RI | 📚 STUDYING: explore_001 (Explore-Exploit)
07:30:00 | RI |    Current: ε=0.2, data_points=0
07:30:00 | RI |    Principle says: High uncertainty → High exploration
07:30:00 | RI |    Insight: Should increase ε to 0.5
07:30:01 | RI | ⚖️ PRINCIPLED CHECK: Decision 'scale_gpu_up'
07:30:01 | RI |    Consulting: reversibility_001, patience_002
07:30:01 | RI |    Wisdom: "N < 30 → small updates only"
07:30:01 | RI |    Verdict: APPROVED (reversible, low risk)
```

---

## Success Criteria

### Behavioral Changes

1. **Exploration increases** when uncertainty is high
2. **Belief updates are proportional** to evidence strength
3. **Irreversible actions are delayed** when confidence is low
4. **Wisdom accumulates** and is reused

### Measurable Outcomes

| Metric | Target | How Measured |
|--------|--------|--------------|
| Principles studied | 40+ | Count in curriculum |
| Wisdom entries created | 20+ after 1 week | Count in wisdom.json |
| Behavioral changes made | 5+ | Log count |
| Decision overrides by principle | At least 1 | Principled reasoner logs |
| Calibration improvement | +10% accuracy | Meta-intelligence tracking |

### Philosophical Outcomes

- System can articulate *why* it made a decision, citing principles
- System knows what it doesn't know (epistemic humility)
- System's behavior changes based on learned wisdom, not just rules
- System aligns with SOURCE principles in ambiguous situations

---

## File Summary

| File | Purpose |
|------|---------|
| `curriculum/` | Intelligence principles organized by domain |
| `self_study.py` | Engine that studies principles and applies them |
| `wisdom_store.py` | Manages local and Mem0 wisdom storage |
| `principled_reasoner.py` | Validates decisions against principles |
| `study_scheduler.py` | Manages study rhythm and focus |

---

## Next Steps

1. **Seed the curriculum** with the 40 initial principles
2. **Build self-study engine** with application and reflection logic
3. **Create principled reasoner** and integrate into deciding.py
4. **Set up study scheduler** for daily/weekly rhythm
5. **Connect to Mem0** for long-term wisdom storage
6. **Update core.py** to include study phase
7. **Add dashboard panel** showing study progress and wisdom

---

## The End State

A system that:

- **Knows how to think** before it has data to think about
- **Reasons from principles** rather than just following rules
- **Gets wiser over time** through structured self-reflection
- **Makes better decisions** by consulting accumulated wisdom
- **Aligns with your values** (SOURCE, love economics) in every action

When users arrive, it won't be starting from zero—it will be **philosophically prepared** to learn from them intelligently.















