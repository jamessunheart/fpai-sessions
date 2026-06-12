"""Capability Probe Harness — the honest spine of compounding measurement.

Fixed task set. Weekly run. Claude-judged pass/fail + quality score.
Probes are append-only (versioned); never deleted, never modified.
This is the baseline that makes real compounding provable.
"""

from .probes import PROBES, PROBE_VERSION, Probe
from .runner import run_all_probes, run_probe
from .results import (
    latest_run_summary,
    results_since,
    compounding_delta,
    RESULTS_PATH,
)

__all__ = [
    "PROBES", "PROBE_VERSION", "Probe",
    "run_all_probes", "run_probe",
    "latest_run_summary", "results_since", "compounding_delta",
    "RESULTS_PATH",
]
