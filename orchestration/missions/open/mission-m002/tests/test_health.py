"""Tests for the health endpoint."""
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_service_metadata() -> None:
    """The /health endpoint should expose service metadata."""

    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == settings.service_name
    assert payload["environment"] == settings.environment
    assert payload["version"] == settings.version

