"""Tests for telemetry endpoints."""
from fastapi.testclient import TestClient

from app.main import app

# Use a context manager to trigger the lifespan startup event (DB table creation)
def test_create_and_list_telemetry() -> None:
    """Verify that telemetry events can be posted and retrieved."""

    with TestClient(app) as client:
        # 1. Post a new event
        payload = {
            "source": "test-agent-001",
            "event_type": "unit_test_execution",
            "payload": {"status": "success", "duration_ms": 120},
        }
        response = client.post("/telemetry", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == payload["source"]
        assert "id" in data
        assert "timestamp" in data

        # 2. Verify it appears in the feed
        list_response = client.get("/telemetry")
        assert list_response.status_code == 200
        events = list_response.json()
        assert len(events) >= 1
        assert events[0]["id"] == data["id"]

