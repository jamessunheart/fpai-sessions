"""Reusable Mission Control telemetry client."""
import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class TelemetryClient:
    """Fire-and-forget HTTP client for Mission Control telemetry."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 2):
        self.base_url = base_url or os.getenv("MISSION_CONTROL_URL", "http://198.54.123.234:8010")
        self.timeout = timeout
        self.session = requests.Session()

    def capture(self, source: str, event_type: str, payload: Dict[str, Any]) -> bool:
        """Send a telemetry event. Returns False on failure but never raises."""

        endpoint = f"{self.base_url}/telemetry"
        data = {"source": source, "event_type": event_type, "payload": payload}
        try:
            response = self.session.post(endpoint, json=data, timeout=self.timeout)
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Telemetry send failure to %s: %s", endpoint, exc)
            return False

    def get_mission_status(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Fetch aggregated mission status, returning None on 404 or failure."""

        endpoint = f"{self.base_url}/missions/{mission_id}/status"
        try:
            response = self.session.get(endpoint, timeout=self.timeout)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("Telemetry status fetch failure: %s", exc)
            return None

