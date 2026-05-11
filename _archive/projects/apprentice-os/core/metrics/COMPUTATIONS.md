# Metric Computations

> How metrics are calculated in Apprentice OS.

## Coherence Score

**Definition:** Measure of steward's nervous system regulation and decision clarity.

**Computation:**
```python
coherence_score = (
    (100 - stress_level) * 0.4 +
    decision_quality * 100 * 0.3 +
    sleep_quality * 0.2 +
    self_reported_clarity * 0.1
)
```

**Sources:**
- `stress_level`: Self-reported (0-100)
- `decision_quality`: Override rate inverse (0-1)
- `sleep_quality`: Self-reported or inferred (0-100)
- `self_reported_clarity`: Direct input (0-100)

---

## Stress Accumulation (Shadow Cost)

**Definition:** Compound pressure on steward nervous system.

**Computation:**
```python
stress_accumulation = (
    self_reported_stress * 0.4 +
    interaction_pattern_score * 0.3 +
    decision_quality_delta * 0.3
)

interaction_pattern_score = (
    COUNT(response_gaps > 24h) * 10 +
    COUNT(override_events) * 5
)

decision_quality_delta = (
    baseline_decision_quality - current_decision_quality
) * 100
```

---

## Trust Decay (Shadow Cost)

**Definition:** Erosion of relational capital.

**Computation:**
```python
trust_decay = (
    latency_score * 0.25 +
    friction_score * 0.35 +
    feedback_delta * 0.4
)

latency_score = AVG(response_time) / expected_response_time * 100
friction_score = COUNT(clarification_events) / COUNT(total_interactions) * 100
feedback_delta = previous_trust_score - current_trust_score
```

---

## Optionality Loss (Shadow Cost)

**Definition:** Closing future paths through commitments.

**Computation:**
```python
optionality_loss = (
    (5 - AVG(reversibility_scores)) * 20 +
    lock_in_count * 10
)
```

**Reversibility Scale:**
- 5: Easily reversible (soft commitment)
- 4: Reversible with effort
- 3: Partially reversible
- 2: Mostly irreversible
- 1: Completely irreversible (burned bridge)

---

## Complexity Creep (Shadow Cost)

**Definition:** Incremental additions exceeding coherence capacity.

**Computation:**
```python
current_complexity = entity_count * (1 + connection_density) * log(rule_count)
complexity_creep = current_complexity / baseline_complexity

entity_count = COUNT(apprentices) + COUNT(assistants) + COUNT(modules)
connection_density = COUNT(relationships) / entity_count
```

---

## Apprentice Autonomy Score

**Definition:** How much independent authority an apprentice has.

**Computation:**
```python
autonomy_score = (
    decision_authority_level * 0.4 +
    oversight_inverse * 0.3 +
    proactive_contribution_rate * 0.3
)

decision_authority_level = COUNT(autonomous_decisions) / COUNT(total_decisions) * 100
oversight_inverse = 100 - (check_in_frequency * 10)
proactive_contribution_rate = COUNT(proactive_actions) / COUNT(total_actions) * 100
```

---

## Loop Improvement Score

**Definition:** Whether an apprentice loop is progressing.

**Computation:**
```python
loop_improvement = (
    trust_delta * 0.3 +
    autonomy_delta * 0.3 +
    stress_inverse_delta * 0.2 +
    output_quality_delta * 0.2
)
```

A positive score indicates the loop is healthy and growing.
A negative score indicates potential extraction or misalignment.

---

*This document defines metric computations for Apprentice OS.*


