#!/usr/bin/env python3
"""Conversation OS — two-gate knowledge-promotion boundary (INERT).

Contract + rules only. NOT connected to any Brain writer. evaluate() returns a
decision object; it never persists or emits anything externally.

Two INDEPENDENT dimensions (never collapsed into one):
  - durability  : transient | candidate | durable | superseded   (should it last?)
  - verification: inferred | user-confirmed | reality-proven      (is it true?)
  - audience    : PRIVATE | COUNCIL | PUBLIC                        (who may see?)

Hard rule: audience alone NEVER promotes. Being PRIVATE (or PUBLIC) is not
evidence of durability or truth. Promotion requires the durability gate AND the
verification gate AND an approval actor/policy — audience only travels along.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DURABILITY = ("transient", "candidate", "durable", "superseded")
VERIFICATION = ("inferred", "user-confirmed", "reality-proven")
AUDIENCE = ("PRIVATE", "COUNCIL", "PUBLIC")

# Gate thresholds (independent).
_PROMOTABLE_DURABILITY = {"durable"}
_PROMOTABLE_VERIFICATION = {"user-confirmed", "reality-proven"}


@dataclass(frozen=True)
class MemoryCandidate:
    content: str
    durability: str
    verification: str
    audience: str
    source_event_id: str
    source_conversation_id: str
    approval_actor: str | None = None      # human/policy that approved, if any
    approval_policy: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def _validate(c: MemoryCandidate) -> list[str]:
    errs = []
    if c.durability not in DURABILITY:
        errs.append(f"bad durability {c.durability!r}")
    if c.verification not in VERIFICATION:
        errs.append(f"bad verification {c.verification!r}")
    if c.audience not in AUDIENCE:
        errs.append(f"bad audience {c.audience!r}")
    return errs


def evaluate(c: MemoryCandidate) -> dict[str, Any]:
    """Return a decision. INERT — no side effects, no Brain write."""
    errs = _validate(c)
    if errs:
        return {"result": "rejected", "reason": "invalid: " + "; ".join(errs)}

    reasons = []
    durability_ok = c.durability in _PROMOTABLE_DURABILITY
    verification_ok = c.verification in _PROMOTABLE_VERIFICATION
    approval_ok = bool(c.approval_actor or c.approval_policy)
    if not durability_ok:
        reasons.append(f"durability gate: {c.durability} not in {sorted(_PROMOTABLE_DURABILITY)}")
    if not verification_ok:
        reasons.append(f"verification gate: {c.verification} not in {sorted(_PROMOTABLE_VERIFICATION)}")
    if not approval_ok:
        reasons.append("approval gate: no approval actor or policy")

    if durability_ok and verification_ok and approval_ok:
        return {
            "result": "knowledge.promoted",
            "durability": c.durability,
            "verification": c.verification,
            "audience": c.audience,          # travels along; did NOT gate
            "approved_by": c.approval_actor or c.approval_policy,
            "source_event_id": c.source_event_id,
            "source_conversation_id": c.source_conversation_id,
            "inert": True,                   # not written anywhere
        }
    return {"result": "rejected", "reason": "; ".join(reasons), "audience": c.audience}
