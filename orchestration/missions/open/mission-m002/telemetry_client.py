"""Compatibility shim for the shared Mission Control TelemetryClient."""
import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parent.parent / "shared"
if SHARED_DIR.exists():
    sys.path.append(str(SHARED_DIR))

from telemetry_client import TelemetryClient  # type: ignore

__all__ = ("TelemetryClient",)

