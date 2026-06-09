"""Self-cost awareness — aggregates budget_ledger + limits for optimization.

The model cannot optimize what it cannot see. This package turns ledger
rows into structured intelligence and a short natural-language block for
the companion context."""

from .analytics import cost_report, cost_context_block
from .rollup import cost_reconciliation_report, cost_rollup_report

COST_INTEL_VERSION = "1.1.0"

__all__ = [
    "cost_report",
    "cost_context_block",
    "cost_rollup_report",
    "cost_reconciliation_report",
    "COST_INTEL_VERSION",
]
