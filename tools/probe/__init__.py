"""Probe outreach subsystem.

The package is safe to import in tests and build scans. Live sends are delegated
to a Hermes adapter when one is present; this package does not auto-populate
contacts or bypass James-owned outreach gates.
"""

