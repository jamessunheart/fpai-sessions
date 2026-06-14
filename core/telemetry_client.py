import logging
import os
import requests
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class TelemetryClient:
    def __init__(self, base_url: Optional[str] = None, timeout: int = 2):
        self.base_url = base_url or os.getenv("MISSION_CONTROL_URL", "http://198.54.123.234:8010")
        self.timeout = timeout
        self.session = requests.Session()

    def capture(self, source: str, event_type: str, payload: Dict[str, Any]) -> bool:
        """Fire-and-forget telemetry event."""
        endpoint = f"{self.base_url}/telemetry"
        try:
            self.session.post(endpoint, json={
                "source": source,
                "event_type": event_type,
                "payload": payload
            }, timeout=self.timeout)
            return True
        except Exception as e:
            logger.warning(f"Telemetry failed: {e}")
            return False

