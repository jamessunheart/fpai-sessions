"""API endpoint tests for I PROACTIVE"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "I PROACTIVE"
    assert data["droplet_id"] == 20


def test_health():
    """Test health endpoint (UBIC compliance)"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["droplet_id"] == 20
    assert data["service_name"] == "i-proactive"
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "uptime_seconds" in data


def test_capabilities():
    """Test capabilities endpoint (UBIC compliance)"""
    response = client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["droplet_id"] == 20
    assert len(data["capabilities"]) > 0
    assert "Multi-agent task orchestration" in data["capabilities"][0]


def test_state():
    """Test state endpoint (UBIC compliance)"""
    response = client.get("/state")
    assert response.status_code == 200
    data = response.json()
    assert data["droplet_id"] == 20
    assert "queued_tasks" in data
    assert "running_tasks" in data


def test_dependencies():
    """Test dependencies endpoint (UBIC compliance)"""
    response = client.get("/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert data["droplet_id"] == 20
    assert len(data["dependencies"]) > 0


def test_create_task():
    """Test task creation"""
    response = client.post(
        "/tasks/create",
        params={
            "title": "Test task",
            "description": "This is a test task",
            "priority": "medium"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test task"
    assert "task_id" in data


def test_make_decision():
    """Test strategic decision making"""
    response = client.post(
        "/decisions/make",
        params={
            "title": "Test decision",
            "description": "Should we do A or B?",
            "options": ["A", "B"]
        },
        json={
            "revenue_impact": 0.8,
            "risk_level": 0.3,
            "time_to_value": 30,
            "resource_requirement": 0.5,
            "strategic_alignment": 0.9
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommended_option" in data
    assert data["recommended_option"] in ["A", "B"]


def test_treasury_decision():
    """Test treasury deployment decision"""
    response = client.post(
        "/decisions/treasury",
        params={
            "available_capital_usd": 50000,
            "current_revenue_monthly": 25000,
            "cycle_position": "mid"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "should_deploy" in data
    assert "amount_to_deploy_usd" in data


def test_revenue_recording():
    """Test revenue recording"""
    response = client.post(
        "/revenue/record",
        params={
            "service_name": "test-service",
            "amount_usd": 5000,
            "source": "test"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["amount_usd"] == 5000


def test_revenue_stats():
    """Test revenue statistics"""
    response = client.get("/revenue/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue_usd" in data
    assert "by_service" in data


def test_memory_summary():
    """Test memory summary"""
    response = client.get("/memory/summary")
    assert response.status_code == 200
    data = response.json()
    assert "decisions_count" in data
    assert "task_patterns_count" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
