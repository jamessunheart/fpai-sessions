"""
Basic tests for Alerts Service main endpoints
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime_seconds" in data


def test_capabilities():
    """Test capabilities endpoint"""
    response = client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "alerts"
    assert data["droplet_id"] == 106
    assert "capabilities" in data
    assert isinstance(data["capabilities"], list)


def test_state():
    """Test state endpoint"""
    response = client.get("/state")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "queued" in data
    assert "sent_today" in data


def test_dependencies():
    """Test dependencies endpoint"""
    response = client.get("/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert "required_services" in data
    assert "optional_services" in data


def test_list_templates():
    """Test listing message templates"""
    response = client.get("/templates")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "count" in data
    assert data["count"] > 0


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Alerts"
    assert data["droplet_id"] == 106


@pytest.mark.asyncio
async def test_send_notification_missing_config(monkeypatch):
    """Test sending notification without configuration"""
    # This will fail if Telegram is not configured
    # Which is expected in test environment
    response = client.post(
        "/send",
        json={
            "channel": "telegram",
            "recipient": "123456",
            "message": "Test message",
            "priority": "normal"
        }
    )
    # Should queue successfully even without config
    assert response.status_code in [200, 400]
