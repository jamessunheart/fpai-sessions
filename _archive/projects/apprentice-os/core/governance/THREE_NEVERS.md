# THREE NEVERS - Inviolable Constraints

> These constraints CANNOT be overridden. They are hardcoded and enforced at multiple layers.

## The Three Nevers

### 1. NEVER optimize for yield at the expense of coherence or circulation

**What this means:**
- If a decision improves financial returns but increases steward stress → **REJECT**
- If a decision accelerates output but reduces value flow to builders → **REJECT**
- If a decision hits a metric target but breaks relationship health → **REJECT**

**Enforcement:**
- Decision Engine blocks any action where `yield_benefit > 0` AND `coherence_impact < 0`
- Shadow cost ratio > 1.0 triggers automatic hold

---

### 2. NEVER introduce complexity faster than the steward can remain regulated

**What this means:**
- Adding new apprentices, modules, projects, or connections must not outpace coherence
- If the steward is already at capacity, no new complexity enters
- Growth happens at the pace of integration, not the pace of opportunity

**Enforcement:**
- If `steward_stress > 60` AND `complexity_delta > 0` → **BLOCK**
- If `coherence_trend = declining` AND `complexity_delta > 0.2` → **BLOCK**
- If `coherence < baseline` AND `complexity_delta > 0` → **BLOCK**

---

### 3. NEVER treat debt as permanent

**What this means:**
- All debt (financial, relational, technical, energetic) has a resolution path
- No debt entry exists without a target resolution date
- Debt that persists beyond 90 days without progress triggers escalation

**Enforcement:**
- `creates_debt = true` AND `has_resolution_path = false` → **BLOCK**
- Debt entries > 90 days old without progress → **ESCALATE**
- Cannot add new debt while critical unresolved debt exists

---

## Why These Cannot Be Overridden

The purpose is not to prevent all risk-taking. It is to ensure that risk-taking
**NEVER compromises the foundation on which everything else is built.**

If you find yourself wanting to override a Never, that is signal. **Pause. Ask why.**
The constraint is pointing at something.

---

## Attempted Override Protocol

When someone attempts to override a Never:

1. The attempt is **LOGGED** permanently
2. The action is **DENIED**
3. A message is returned:

> "The THREE NEVERS cannot be overridden. [NEVER_TYPE] is inviolable. 
> Your attempt has been logged. If you're trying to override, ask why 
> the constraint is blocking you. The constraint is pointing at something important."

---

## Audit Trail

All Never violations and override attempts are permanently recorded:

```json
{
  "timestamp": "2025-12-24T19:00:00Z",
  "never_type": "YIELD_OVER_COHERENCE",
  "action_attempted": "Deploy high-risk feature",
  "severity": 0.85,
  "evidence": ["Yield benefit (+0.5) while harming coherence (-0.3)"],
  "result": "BLOCKED"
}
```

---

*This document is the source of truth for inviolable constraints in Apprentice OS.*


