"""
Tests for UDC compliance endpoints
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test /health endpoint returns correct format"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert 'id' in data
    assert 'name' in data
    assert 'steward' in data
    assert 'status' in data
    assert data['status'] in ['active', 'inactive', 'error']
    assert 'endpoint' in data
    assert 'updated_at' in data


def test_capabilities_endpoint():
    """Test /capabilities endpoint"""
    response = client.get("/capabilities")

    assert response.status_code == 200
    data = response.json()

    assert 'version' in data
    assert 'features' in data
    assert 'dependencies' in data
    assert 'udc_version' in data
    assert isinstance(data['features'], list)


def test_state_endpoint():
    """Test /state endpoint"""
    response = client.get("/state")

    assert response.status_code == 200
    data = response.json()

    assert 'cpu_percent' in data
    assert 'memory_mb' in data
    assert 'uptime_seconds' in data
    assert 'requests_total' in data


def test_dependencies_endpoint():
    """Test /dependencies endpoint"""
    response = client.get("/dependencies")

    assert response.status_code == 200
    data = response.json()

    assert 'required' in data
    assert 'optional' in data
    assert 'missing' in data
    assert isinstance(data['required'], list)


def test_leverage_calculation_endpoint():
    """Test /api/leverage/calculate endpoint"""
    response = client.post("/api/leverage/calculate", json={
        "primary_magnet_price": 44000.0,
        "current_price": 43200.0,
        "magnet_strength": 70.0,
        "conflict_index": 0.3,
        "volatility_pressure": 1.0,
        "atr": 450.0
    })

    assert response.status_code == 200
    data = response.json()

    assert 'leverage' in data
    assert 'components' in data
    assert 'is_high_tension' in data


if __name__ == "__main__":
    test_health_endpoint()
    test_capabilities_endpoint()
    test_state_endpoint()
    test_dependencies_endpoint()
    test_leverage_calculation_endpoint()
    print("✅ All UDC tests passed!")
