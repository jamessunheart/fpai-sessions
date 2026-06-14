"""
WhiteRock Blessings Engine - Health Endpoint Tests
Tests for UDC-compliant health endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check returns active status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["active", "inactive", "error"]
    assert data["service"] == "WhiteRock Blessings Engine"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_capabilities(client: AsyncClient):
    """Test capabilities endpoint returns feature list."""
    response = await client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "features" in data
    assert isinstance(data["features"], list)
    # Verify no treasury/trading features
    assert "firewall_enforced" in data
    for forbidden in data["firewall_enforced"]:
        assert "trade" in forbidden.lower() or "treasury" in forbidden.lower() or "position" in forbidden.lower()


@pytest.mark.asyncio
async def test_state(client: AsyncClient):
    """Test state endpoint returns resource metrics."""
    response = await client.get("/state")
    assert response.status_code == 200
    data = response.json()
    assert "total_members" in data
    assert "active_blessing_requests" in data
    assert "cora_in_circulation" in data
    assert "capacity_level" in data


@pytest.mark.asyncio
async def test_dependencies(client: AsyncClient):
    """Test dependencies endpoint returns integration status."""
    response = await client.get("/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert "dependencies" in data
    assert isinstance(data["dependencies"], list)



