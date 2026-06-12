"""API endpoint tests for Autonomous Executor"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Autonomous Executor"
    assert "endpoints" in data


def test_health_endpoint():
    """Test UDC health endpoint"""
    response = client.get("/executor/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert data["version"] == "1.0.0"


def test_capabilities_endpoint():
    """Test UDC capabilities endpoint"""
    response = client.get("/executor/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["can_build_droplets"] is True
    assert data["can_generate_specs"] is True
    assert "supported_approval_modes" in data


def test_build_droplet_validation():
    """Test build droplet endpoint validates input"""
    # Missing required field
    response = client.post("/executor/build-droplet", json={})
    assert response.status_code == 422  # Validation error

    # Valid request
    response = client.post("/executor/build-droplet", json={
        "architect_intent": "Build test droplet",
        "approval_mode": "auto"
    })
    assert response.status_code == 200
    data = response.json()
    assert "build_id" in data
    assert "status" in data
    assert "stream_url" in data


def test_get_build_status_not_found():
    """Test getting status for non-existent build"""
    response = client.get("/executor/builds/nonexistent/status")
    assert response.status_code == 404


def test_list_builds():
    """Test listing builds"""
    response = client.get("/executor/builds")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
