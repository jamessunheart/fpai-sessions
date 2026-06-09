"""Field Sensor — FPI's self-awareness organ.

Three-layer architecture:
  1. sensors.py  — cheap continuous watchers on the AI field
  2. gate.py     — local significance heuristics (99% filter rate)
  3. reflect.py  — Claude-powered deep reflection on gated events
  4. registry.py — append-only memory (gap_registry.jsonl)

Cadence is event-driven, not time-driven. The system breathes
when the field breathes.
"""

from .registry import append_gap, capabilities_snapshot, BRAIN_DIR, REGISTRY_PATH
from .sensors import sense_once, SensedEvent
from .gate import significance_score, passes_gate, GATE_VERSION
from .reflect import reflect_on_event
from .scheduler import run_field_sensor_cycle

__all__ = [
    "append_gap", "capabilities_snapshot", "BRAIN_DIR", "REGISTRY_PATH",
    "sense_once", "SensedEvent",
    "significance_score", "passes_gate", "GATE_VERSION",
    "reflect_on_event",
    "run_field_sensor_cycle",
]
