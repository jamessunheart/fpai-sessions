"""Pulse — real outward-outcome telemetry.

The causal bridge between internal compounding and external reality.
If sense/gate/reflect/propose/probe all improve but Pulse metrics
don't move, compounding is theater. Pulse keeps the whole stack honest.

Three sections:
  - zen_village: bookings, passes, revenue, event momentum
  - reach: audience, subscribers, site traffic, outbound signal
  - system: proposal throughput, probe scores, field sensor activity

Snapshots taken weekly into /opt/fpai/brain/pulse_snapshots.jsonl.
Deltas computed between snapshots to prove compounding.
"""

from .collector import collect_pulse, save_snapshot, PULSE_VERSION
from .deltas import weekly_deltas, pulse_history
from .hypothesis import attach_hypothesis_to_proposal, evaluate_proposal_outcomes

__all__ = [
    "collect_pulse", "save_snapshot", "PULSE_VERSION",
    "weekly_deltas", "pulse_history",
    "attach_hypothesis_to_proposal", "evaluate_proposal_outcomes",
]
