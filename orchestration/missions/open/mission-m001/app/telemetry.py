"""Telemetry helper for reusing the shared client."""
import sys
from pathlib import Path
from typing import Final

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
if SHARED_DIR.exists():
    sys.path.append(str(SHARED_DIR))

try:
    from telemetry_client import TelemetryClient  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback if shared missing
    TelemetryClient = None  # type: ignore

client: Final[TelemetryClient | None] = TelemetryClient() if TelemetryClient else None

