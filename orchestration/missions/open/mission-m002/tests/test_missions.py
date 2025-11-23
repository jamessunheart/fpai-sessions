"""Tests for mission status aggregation."""
from fastapi.testclient import TestClient

from app.api.schemas import MissionState
from app.main import app


def test_mission_status_lifecycle() -> None:
    """Verify that telemetry events correctly update mission status."""
    mission_id = "M099_test_mission"

    with TestClient(app) as client:
        # 1. Verify 404 for unknown mission
        response = client.get(f"/missions/{mission_id}/status")
        assert response.status_code == 404

        # 2. Send 'mission_start' event
        client.post("/telemetry", json={
            "source": "orchestrator",
            "event_type": "mission_start",
            "payload": {"mission_id": mission_id, "objective": "Conquer the stars"}
        })

        # 3. Send 'agent_active' event
        client.post("/telemetry", json={
            "source": "agent-007",
            "event_type": "agent_active",
            "payload": {"mission_id": mission_id}
        })

        # 4. Query status
        response = client.get(f"/missions/{mission_id}/status")
        assert response.status_code == 200
        data = response.json()

        assert data["mission_id"] == mission_id
        assert data["state"] == MissionState.IN_PROGRESS
        assert data["current_objective"] == "Conquer the stars"
        assert data["active_agents"] == 1

        # 5. Send 'mission_complete' event
        client.post("/telemetry", json={
            "source": "orchestrator",
            "event_type": "mission_complete",
            "payload": {"mission_id": mission_id}
        })

        # 6. Verify completion
        response = client.get(f"/missions/{mission_id}/status")
        data = response.json()
        assert data["state"] == MissionState.COMPLETED

