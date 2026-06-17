"""Network economy substrate helpers.

The package is intentionally side-effect free. Modules accept fixture or
DB-shaped rows and return shaped recommendations, metrics, or ledger entries.
Live persistence, treasury changes, wallet transactions, and outreach sends
remain separate James/Ember-gated work.
"""
from __future__ import annotations

