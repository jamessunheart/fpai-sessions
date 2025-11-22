"""
Health Endpoint Tests
Per CODE_STANDARDS.md - testing requirements
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """
    Health endpoint should return 200 OK.
    Per UDC_COMPLIANCE.md - required endpoint.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_includes_required_fields():
    """
    Health endpoint should include all UDC required fields.
    Per UDC_COMPLIANCE.md spec.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()
        
        # Required fields per UDC_COMPLIANCE.md
        assert "id" in data
        assert "name" in data
        assert "steward" in data
        assert "status" in data
        assert "endpoint" in data
        assert "updated_at" in data
        
        # Verify values
        assert data["id"] == 12
        assert data["name"] == "Chat Orchestrator"
        assert data["steward"] == "Zainab"


@pytest.mark.asyncio
async def test_health_status_is_valid_enum():
    """
    Health status must be one of: active, inactive, error.
    Per UDC_COMPLIANCE.md - exact enum values required.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()
        
        assert data["status"] in ["active", "inactive", "error"]


@pytest.mark.asyncio
async def test_health_endpoint_response_time():
    """
    Health endpoint should respond in <500ms.
    Per UDC_COMPLIANCE.md - response time requirement.
    """
    import time
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        start = time.time()
        response = await client.get("/health")
        duration = (time.time() - start) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert duration < 500, f"Health endpoint took {duration}ms (should be <500ms)"


@pytest.mark.asyncio
async def test_capabilities_endpoint_returns_200():
    """Capabilities endpoint should return 200 OK"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/capabilities")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_capabilities_includes_features():
    """Capabilities should declare droplet features"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/capabilities")
        data = response.json()
        
        assert "features" in data
        assert "dependencies" in data
        assert "udc_version" in data
        
        # Check key features
        assert "natural_language_understanding" in data["features"]
        assert "conversation_memory" in data["features"]


@pytest.mark.asyncio
async def test_root_endpoint():
    """Root endpoint should return droplet info"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["droplet_id"] == 12
        assert data["name"] == "Chat Orchestrator"